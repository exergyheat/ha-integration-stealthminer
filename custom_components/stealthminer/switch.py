"""Switch platform for Stealthminer."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
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
    """Set up Stealthminer switches from a config entry."""
    coordinator: StealthminerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        StealthminerATMSwitch(coordinator),
        StealthminerCurtailSwitch(coordinator),
    ]

    async_add_entities(entities)


class StealthminerATMSwitch(CoordinatorEntity[StealthminerDataUpdateCoordinator], SwitchEntity):
    """Switch to control ATM (Auto-Tuning Mode)."""

    _attr_has_entity_name = True
    _attr_name = "ATM"
    _attr_icon = "mdi:auto-fix"

    def __init__(self, coordinator: StealthminerDataUpdateCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.api.host}_{coordinator.api.port}_atm_switch"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        """Return true if ATM is enabled."""
        if not self.coordinator.data or not self.coordinator.data.get("online", False):
            return None

        atm = self.coordinator.data.get("atm", {})
        return atm.get("Enabled", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on ATM."""
        try:
            await self.coordinator.api.set_atm(True)
            await self.coordinator.async_request_refresh()
        except StealthminerAPIError as err:
            _LOGGER.error("Error enabling ATM: %s", err)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off ATM."""
        try:
            await self.coordinator.api.set_atm(False)
            await self.coordinator.async_request_refresh()
        except StealthminerAPIError as err:
            _LOGGER.error("Error disabling ATM: %s", err)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.coordinator.data.get("online", False)
        )


class StealthminerCurtailSwitch(CoordinatorEntity[StealthminerDataUpdateCoordinator], SwitchEntity):
    """Switch to control miner curtailment (sleep mode)."""

    _attr_has_entity_name = True
    _attr_name = "Sleep Mode"
    _attr_icon = "mdi:sleep"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: StealthminerDataUpdateCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.api.host}_{coordinator.api.port}_curtail_switch"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        """Return true if miner is in sleep mode (curtailed)."""
        if not self.coordinator.data or not self.coordinator.data.get("online", False):
            return None

        config = self.coordinator.data.get("config", {})
        curtail_mode = config.get("CurtailMode", "None")
        # Sleep mode is when CurtailMode is not "None"
        return curtail_mode != "None"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Put miner to sleep."""
        try:
            await self.coordinator.api.curtail_sleep()
            await self.coordinator.async_request_refresh()
        except StealthminerAPIError as err:
            _LOGGER.error("Error putting miner to sleep: %s", err)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Wake up miner."""
        try:
            await self.coordinator.api.curtail_wakeup()
            await self.coordinator.async_request_refresh()
        except StealthminerAPIError as err:
            _LOGGER.error("Error waking up miner: %s", err)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.coordinator.data.get("online", False)
        )
