"""Select platform for Stealthminer."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
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
    """Set up Stealthminer select entities from a config entry."""
    coordinator: StealthminerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        StealthminerProfileSelect(coordinator),
    ]

    async_add_entities(entities)


class StealthminerProfileSelect(CoordinatorEntity[StealthminerDataUpdateCoordinator], SelectEntity):
    """Select entity for choosing mining profile."""

    _attr_has_entity_name = True
    _attr_name = "Profile"
    _attr_icon = "mdi:tune"

    def __init__(self, coordinator: StealthminerDataUpdateCoordinator) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.api.host}_{coordinator.api.port}_profile_select"
        self._attr_device_info = coordinator.device_info

    @property
    def options(self) -> list[str]:
        """Return list of available profiles."""
        if not self.coordinator.data:
            return []

        profiles = self.coordinator.data.get("profiles", [])
        return [p.get("Profile Name", "") for p in profiles if p.get("Profile Name")]

    @property
    def current_option(self) -> str | None:
        """Return the currently selected profile."""
        if not self.coordinator.data or not self.coordinator.data.get("online", False):
            return None

        config = self.coordinator.data.get("config", {})
        return config.get("Profile")

    async def async_select_option(self, option: str) -> None:
        """Change the selected profile."""
        try:
            await self.coordinator.api.set_profile(option)
            _LOGGER.info("Profile changed to %s", option)
            await self.coordinator.async_request_refresh()
        except StealthminerAPIError as err:
            _LOGGER.error("Error setting profile to %s: %s", option, err)

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
        """Return additional profile info."""
        if not self.coordinator.data:
            return {}

        profiles = self.coordinator.data.get("profiles", [])
        current = self.current_option

        # Find current profile details
        for profile in profiles:
            if profile.get("Profile Name") == current:
                return {
                    "frequency": profile.get("Frequency"),
                    "voltage": profile.get("Voltage"),
                    "estimated_hashrate_th": profile.get("Hashrate"),
                    "estimated_watts": profile.get("Watts"),
                    "step": profile.get("Step"),
                }

        return {}
