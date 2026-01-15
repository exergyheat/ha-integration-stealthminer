"""Button platform for Stealthminer."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity, ButtonDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
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
    """Set up Stealthminer buttons from a config entry."""
    coordinator: StealthminerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        StealthminerRebootButton(coordinator),
        StealthminerResetMinerButton(coordinator),
        StealthminerWakeUpButton(coordinator),
    ]

    async_add_entities(entities)


class StealthminerRebootButton(CoordinatorEntity[StealthminerDataUpdateCoordinator], ButtonEntity):
    """Button to reboot the miner."""

    _attr_has_entity_name = True
    _attr_name = "Reboot"
    _attr_icon = "mdi:restart"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: StealthminerDataUpdateCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.api.host}_{coordinator.api.port}_reboot"
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            await self.coordinator.api.reboot()
            _LOGGER.info("Reboot command sent to miner")
        except StealthminerAPIError as err:
            _LOGGER.error("Error rebooting miner: %s", err)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.coordinator.data.get("online", False)
        )


class StealthminerResetMinerButton(CoordinatorEntity[StealthminerDataUpdateCoordinator], ButtonEntity):
    """Button to reset the miner application."""

    _attr_has_entity_name = True
    _attr_name = "Reset Miner"
    _attr_icon = "mdi:refresh"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: StealthminerDataUpdateCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.api.host}_{coordinator.api.port}_reset_miner"
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            await self.coordinator.api.reset_miner()
            _LOGGER.info("Reset miner command sent")
            await self.coordinator.async_request_refresh()
        except StealthminerAPIError as err:
            _LOGGER.error("Error resetting miner: %s", err)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.coordinator.data.get("online", False)
        )


class StealthminerWakeUpButton(CoordinatorEntity[StealthminerDataUpdateCoordinator], ButtonEntity):
    """Button to wake up the miner from sleep mode."""

    _attr_has_entity_name = True
    _attr_name = "Wake Up"
    _attr_icon = "mdi:alarm"

    def __init__(self, coordinator: StealthminerDataUpdateCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.api.host}_{coordinator.api.port}_wakeup"
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            await self.coordinator.api.curtail_wakeup()
            _LOGGER.info("Wake up command sent to miner")
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
