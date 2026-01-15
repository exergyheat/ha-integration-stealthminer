"""Number platform for Stealthminer."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower, EntityCategory
from homeassistant.core import HomeAssistant, callback, CALLBACK_TYPE
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import StealthminerAPIError
from .const import DOMAIN
from .coordinator import StealthminerDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Stealthminer number entities from a config entry."""
    coordinator: StealthminerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    if coordinator.data:
        # Always add Power Limit - works via profile selection on all hardware
        entities.append(StealthminerPowerLimitNumber(coordinator))

    async_add_entities(entities)


class StealthminerPowerLimitNumber(CoordinatorEntity[StealthminerDataUpdateCoordinator], NumberEntity):
    """Number entity for power limit control via profile selection.

    This entity provides a user-friendly way to control miner power consumption
    by automatically selecting the most appropriate profile based on a target
    power limit. It uses an adaptive control loop that:

    1. Takes the user's target power limit (in real-world watts)
    2. Selects an initial profile based on estimated wattage
    3. Monitors actual power consumption after stabilization
    4. Steps UP if too far below target (leaving headroom on the table)
    5. Steps DOWN if over target (exceeding limit)
    6. Stops when within the tolerance band (95-100% of target)

    The tolerance band is 0% to -5% of target - we never exceed the limit,
    but try to get within 5% of it for optimal utilization.

    This approach works on all hardware, unlike the native powertargetset API
    which only supports certain models (S21 series, S19 XP, etc.).
    """

    # Standard S19 has 3 hash boards - API wattages are for full 3-board system
    STANDARD_BOARD_COUNT = 3

    # User-friendly power limit range for single-board systems
    SINGLE_BOARD_MIN_WATTS = 350
    SINGLE_BOARD_MAX_WATTS = 1300

    # Control loop settings
    TOLERANCE_PERCENT = 0.05  # 5% below target is acceptable (0-5% under)
    STABILIZATION_DELAY = 120  # Seconds to wait after profile change before checking
    MAX_ADJUSTMENTS = 5  # Maximum adjustments per control cycle (safety limit)

    _attr_has_entity_name = True
    _attr_name = "Power Limit"
    _attr_icon = "mdi:lightning-bolt"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_mode = NumberMode.SLIDER
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: StealthminerDataUpdateCoordinator) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.api.host}_{coordinator.api.port}_power_limit"
        self._attr_device_info = coordinator.device_info
        self._target_limit: float | None = None

        # Control loop state
        self._control_loop_active: bool = False
        self._adjustments_made: int = 0
        self._loop_status: str = "idle"  # idle, adjusting, within_tolerance, at_limit
        self._cancel_scheduled_check: CALLBACK_TYPE | None = None

        # Initialize limits
        self._update_limits()

    def _get_board_count(self) -> int:
        """Get the number of active boards."""
        if not self.coordinator.data:
            return 1
        return max(1, self.coordinator.data.get("board_count", 1))

    def _get_scale_factor(self) -> float:
        """Get the scaling factor to convert between API watts and real watts.

        API reports wattages for a standard 3-board system.
        For a 1-board system, real watts = API watts / 3.
        """
        return self.STANDARD_BOARD_COUNT / self._get_board_count()

    def _api_watts_to_real(self, api_watts: float) -> float:
        """Convert API-reported watts to real-world watts."""
        return api_watts / self._get_scale_factor()

    def _real_watts_to_api(self, real_watts: float) -> float:
        """Convert real-world watts to API-equivalent watts."""
        return real_watts * self._get_scale_factor()

    def _get_profiles_sorted_by_watts(self) -> list[dict[str, Any]]:
        """Get profiles sorted by wattage (ascending).

        Returns profiles with their API-reported wattage values.
        """
        if not self.coordinator.data:
            return []

        profiles = self.coordinator.data.get("profiles", [])

        valid_profiles = [
            p for p in profiles if p.get("Profile Name") and p.get("Watts")
        ]

        # Sort by watts ascending (lowest power first)
        return sorted(valid_profiles, key=lambda p: p["Watts"])

    def _update_limits(self) -> None:
        """Update min/max based on board count."""
        board_count = self._get_board_count()

        # Scale the limits based on board count
        # For 1 board: 350-1300W, for 3 boards: 1050-3900W
        self._attr_native_min_value = self.SINGLE_BOARD_MIN_WATTS * board_count
        self._attr_native_max_value = self.SINGLE_BOARD_MAX_WATTS * board_count
        self._attr_native_step = 25

    def _find_profile_for_limit(self, real_watts_limit: float) -> dict[str, Any] | None:
        """Find the best profile for a given real-world power limit.

        Converts the limit to API-equivalent watts, then finds the highest
        profile that doesn't exceed that limit.
        """
        profiles = self._get_profiles_sorted_by_watts()

        if not profiles:
            return None

        # Convert real-world limit to API-equivalent
        api_watts_limit = self._real_watts_to_api(real_watts_limit)

        # Find all profiles at or below the API limit
        under_limit = [p for p in profiles if p["Watts"] <= api_watts_limit]

        if under_limit:
            # Return the highest wattage profile that's still under the limit
            return under_limit[-1]
        else:
            # No profile under limit, return the lowest available
            return profiles[0]

    def _get_next_lower_profile(self, current_profile_name: str) -> dict[str, Any] | None:
        """Get the next lower wattage profile."""
        profiles = self._get_profiles_sorted_by_watts()

        for i, profile in enumerate(profiles):
            if profile.get("Profile Name") == current_profile_name:
                if i > 0:
                    return profiles[i - 1]
                return None  # Already at lowest
        return None

    def _get_next_higher_profile(self, current_profile_name: str) -> dict[str, Any] | None:
        """Get the next higher wattage profile."""
        profiles = self._get_profiles_sorted_by_watts()

        for i, profile in enumerate(profiles):
            if profile.get("Profile Name") == current_profile_name:
                if i < len(profiles) - 1:
                    return profiles[i + 1]
                return None  # Already at highest
        return None

    def _get_current_profile_name(self) -> str:
        """Get the name of the currently active profile."""
        if not self.coordinator.data:
            return ""
        config = self.coordinator.data.get("config", {})
        return config.get("Profile", "")

    @property
    def native_value(self) -> float | None:
        """Return the current power limit."""
        if not self.coordinator.data or not self.coordinator.data.get("online", False):
            return None

        # Update limits when data changes
        self._update_limits()

        # Always return the user's target if set - slider stays where user put it
        if self._target_limit is not None:
            return self._target_limit

        # On initial load (no target set yet), default to middle of range
        return (self._attr_native_min_value + self._attr_native_max_value) / 2

    def _get_actual_power(self) -> float:
        """Get the actual current power consumption."""
        if not self.coordinator.data:
            return 0
        power = self.coordinator.data.get("power", {})
        return power.get("Watts", 0)

    def _cancel_pending_check(self) -> None:
        """Cancel any pending control loop check."""
        if self._cancel_scheduled_check is not None:
            self._cancel_scheduled_check()
            self._cancel_scheduled_check = None

    def _schedule_control_loop_check(self) -> None:
        """Schedule the next control loop check after stabilization delay."""
        self._cancel_pending_check()

        @callback
        def _schedule_async_check(_now: Any) -> None:
            """Schedule the async check."""
            self.hass.async_create_task(self._run_control_loop())

        self._cancel_scheduled_check = async_call_later(
            self.hass,
            self.STABILIZATION_DELAY,
            _schedule_async_check,
        )
        _LOGGER.debug(
            "Control loop check scheduled in %s seconds",
            self.STABILIZATION_DELAY,
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set the power limit and start the adaptive control loop.

        This finds an initial profile based on estimated wattage, then
        starts a control loop that monitors actual power and adjusts
        the profile to get as close as possible to the target without
        exceeding it.
        """
        # Cancel any existing control loop
        self._cancel_pending_check()

        self._target_limit = value
        self._control_loop_active = True
        self._adjustments_made = 0
        self._loop_status = "adjusting"

        # Find initial profile based on estimates
        selected_profile = self._find_profile_for_limit(value)

        if not selected_profile:
            _LOGGER.error("No profiles available to set power limit")
            self._control_loop_active = False
            self._loop_status = "idle"
            return

        profile_name = selected_profile.get("Profile Name")
        api_watts = selected_profile.get("Watts", 0)
        estimated_real_watts = self._api_watts_to_real(api_watts)

        _LOGGER.info(
            "Power limit %sW -> initial profile '%s' (API: %sW, estimated: ~%sW)",
            int(value),
            profile_name,
            api_watts,
            int(estimated_real_watts),
        )

        try:
            await self.coordinator.api.set_profile(profile_name)
            await self.coordinator.async_request_refresh()

            # Schedule the control loop to check and adjust
            self._schedule_control_loop_check()

        except StealthminerAPIError as err:
            _LOGGER.error("Error setting profile %s: %s", profile_name, err)
            self._target_limit = None
            self._control_loop_active = False
            self._loop_status = "idle"

    async def _run_control_loop(self) -> None:
        """Run one iteration of the adaptive control loop.

        Checks actual power consumption and adjusts profile if needed:
        - If over target: step DOWN (never exceed the limit)
        - If under (target - tolerance): step UP (get closer to target)
        - If within tolerance band: stop (we're good)

        The tolerance band is 0% to -5% of target, meaning:
        - Upper bound: target (e.g., 1000W) - never exceed
        - Lower bound: target * 0.95 (e.g., 950W) - acceptable minimum
        """
        if not self._control_loop_active or self._target_limit is None:
            self._loop_status = "idle"
            return

        # Safety check: max adjustments
        if self._adjustments_made >= self.MAX_ADJUSTMENTS:
            _LOGGER.warning(
                "Control loop: max adjustments (%s) reached, stopping",
                self.MAX_ADJUSTMENTS,
            )
            self._control_loop_active = False
            self._loop_status = "at_limit"
            return

        # Refresh data to get current power
        await self.coordinator.async_request_refresh()

        actual_power = self._get_actual_power()
        current_profile = self._get_current_profile_name()

        if actual_power <= 0:
            _LOGGER.debug("Control loop: no power reading available, retrying")
            self._schedule_control_loop_check()
            return

        # Calculate bounds
        upper_bound = self._target_limit  # Never exceed
        lower_bound = self._target_limit * (1 - self.TOLERANCE_PERCENT)  # 95% of target

        _LOGGER.debug(
            "Control loop: actual=%sW, target=%sW, bounds=[%sW - %sW], profile='%s'",
            int(actual_power),
            int(self._target_limit),
            int(lower_bound),
            int(upper_bound),
            current_profile,
        )

        # Check if over limit - MUST step down
        if actual_power > upper_bound:
            _LOGGER.warning(
                "Control loop: actual %sW EXCEEDS limit %sW, stepping DOWN",
                int(actual_power),
                int(upper_bound),
            )

            lower_profile = self._get_next_lower_profile(current_profile)

            if lower_profile:
                await self._apply_profile_adjustment(lower_profile, "down")
            else:
                _LOGGER.warning("Already at lowest profile, cannot reduce further")
                self._control_loop_active = False
                self._loop_status = "at_limit"
            return

        # Check if under tolerance - should step up to get closer
        if actual_power < lower_bound:
            _LOGGER.info(
                "Control loop: actual %sW is below target band [%sW - %sW], stepping UP",
                int(actual_power),
                int(lower_bound),
                int(upper_bound),
            )

            higher_profile = self._get_next_higher_profile(current_profile)

            if higher_profile:
                # Before stepping up, estimate if it would exceed the limit
                higher_estimated = self._api_watts_to_real(higher_profile["Watts"])

                if higher_estimated <= upper_bound * 1.1:  # Allow 10% margin for estimation error
                    await self._apply_profile_adjustment(higher_profile, "up")
                else:
                    _LOGGER.info(
                        "Control loop: next profile '%s' estimated at %sW would likely exceed limit, stopping",
                        higher_profile["Profile Name"],
                        int(higher_estimated),
                    )
                    self._control_loop_active = False
                    self._loop_status = "within_tolerance"
            else:
                _LOGGER.info("Already at highest profile")
                self._control_loop_active = False
                self._loop_status = "at_limit"
            return

        # Within tolerance band - we're done!
        _LOGGER.info(
            "Control loop: actual %sW is within target band [%sW - %sW], done!",
            int(actual_power),
            int(lower_bound),
            int(upper_bound),
        )
        self._control_loop_active = False
        self._loop_status = "within_tolerance"

    async def _apply_profile_adjustment(
        self,
        new_profile: dict[str, Any],
        direction: str,
    ) -> None:
        """Apply a profile adjustment and schedule next check."""
        profile_name = new_profile.get("Profile Name")

        try:
            await self.coordinator.api.set_profile(profile_name)
            self._adjustments_made += 1

            _LOGGER.info(
                "Control loop: stepped %s to profile '%s' (adjustment %s/%s)",
                direction,
                profile_name,
                self._adjustments_made,
                self.MAX_ADJUSTMENTS,
            )

            await self.coordinator.async_request_refresh()

            # Schedule next check
            self._schedule_control_loop_check()

        except StealthminerAPIError as err:
            _LOGGER.error("Error adjusting profile: %s", err)
            self._control_loop_active = False
            self._loop_status = "idle"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.coordinator.data.get("online", False)
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}

        board_count = self._get_board_count()
        actual_power = self._get_actual_power()
        current_profile = self._get_current_profile_name()

        attrs: dict[str, Any] = {
            "board_count": board_count,
            "scale_factor": self._get_scale_factor(),
        }

        # Show actual power consumption
        if actual_power:
            attrs["actual_power_watts"] = int(actual_power)

        # Show current profile info
        if current_profile:
            attrs["current_profile"] = current_profile

            # Find profile details
            profiles = self._get_profiles_sorted_by_watts()
            for profile in profiles:
                if profile.get("Profile Name") == current_profile:
                    attrs["profile_frequency_mhz"] = profile.get("Frequency")
                    attrs["profile_api_watts"] = profile.get("Watts")
                    attrs["profile_estimated_watts"] = int(
                        self._api_watts_to_real(profile["Watts"])
                    )
                    break

        # Show target info and tolerance band
        if self._target_limit:
            attrs["target_limit_watts"] = int(self._target_limit)
            attrs["tolerance_band_lower"] = int(
                self._target_limit * (1 - self.TOLERANCE_PERCENT)
            )
            attrs["tolerance_band_upper"] = int(self._target_limit)

            # Show if within/over/under
            if actual_power:
                if actual_power > self._target_limit:
                    attrs["power_status"] = "over_limit"
                elif actual_power >= self._target_limit * (1 - self.TOLERANCE_PERCENT):
                    attrs["power_status"] = "within_tolerance"
                else:
                    attrs["power_status"] = "under_target"

        # Control loop status
        attrs["control_loop_active"] = self._control_loop_active
        attrs["control_loop_status"] = self._loop_status
        attrs["adjustments_made"] = self._adjustments_made
        attrs["max_adjustments"] = self.MAX_ADJUSTMENTS

        return attrs
