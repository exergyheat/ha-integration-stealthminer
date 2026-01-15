"""Binary sensor platform for Exergy - Stealthminer."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import StealthminerDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Binary sensor definitions: (key, name, device_class, icon, value_path, value_fn, on_value, entity_category)
BINARY_SENSOR_TYPES: list[tuple] = [
    ("miner_online", "Miner Online", BinarySensorDeviceClass.CONNECTIVITY, None, "online", None, True, None),
    ("pool_connected", "Pool Connected", BinarySensorDeviceClass.CONNECTIVITY, None, None, "pool_connected", True, None),
    ("atm_enabled", "ATM Enabled", None, "mdi:auto-fix", "atm.Enabled", None, True, None),
    ("is_mining", "Is Mining", BinarySensorDeviceClass.RUNNING, None, "config.CurtailMode", None, "None", None),
    ("psu_reporting", "PSU Reporting", None, "mdi:power-plug", "power.PSU", None, True, EntityCategory.DIAGNOSTIC),
    ("is_tuning", "Is Tuning", None, "mdi:tune-vertical", "config.IsTuning", None, True, EntityCategory.DIAGNOSTIC),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Stealthminer binary sensors from a config entry."""
    coordinator: StealthminerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for sensor_type in BINARY_SENSOR_TYPES:
        key, name, device_class, icon, value_path, value_fn, on_value, entity_category = sensor_type
        entities.append(
            StealthminerBinarySensor(
                coordinator=coordinator,
                key=key,
                name=name,
                device_class=device_class,
                icon=icon,
                value_path=value_path,
                value_fn=value_fn,
                on_value=on_value,
                entity_category=entity_category,
            )
        )

    async_add_entities(entities)


class StealthminerBinarySensor(CoordinatorEntity[StealthminerDataUpdateCoordinator], BinarySensorEntity):
    """Representation of a Stealthminer binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: StealthminerDataUpdateCoordinator,
        key: str,
        name: str,
        device_class: BinarySensorDeviceClass | None,
        icon: str | None,
        value_path: str | None,
        value_fn: str | None,
        on_value: Any,
        entity_category: EntityCategory | None,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._key = key
        self._value_path = value_path
        self._value_fn = value_fn
        self._on_value = on_value

        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_icon = icon
        self._attr_entity_category = entity_category
        self._attr_unique_id = f"{coordinator.api.host}_{coordinator.api.port}_{key}"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data:
            return None

        # Special handling for miner online status
        if self._key == "miner_online":
            return self.coordinator.data.get("online", False)

        # If miner is offline, other sensors are unavailable
        if not self.coordinator.data.get("online", False):
            return None

        # Handle computed values
        if self._value_fn:
            value = self._get_computed_value(self._value_fn)
        elif self._value_path:
            value = self._get_path_value(self._value_path)
        else:
            return None

        if value is None:
            return None

        # Compare with on_value
        return value == self._on_value

    def _get_path_value(self, path: str) -> Any:
        """Get value from data using dot notation path."""
        keys = path.split(".")
        data = self.coordinator.data

        for key in keys:
            if isinstance(data, dict):
                data = data.get(key)
            elif isinstance(data, list) and data:
                data = data[0].get(key) if isinstance(data[0], dict) else None
            else:
                return None

            if data is None:
                return None

        return data

    def _get_computed_value(self, key: str) -> Any:
        """Get a computed value."""
        data = self.coordinator.data

        if key == "pool_connected":
            return data.get("pool_connected", False)

        return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Online sensor is always available if coordinator is working
        if self._key == "miner_online":
            return self.coordinator.last_update_success

        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.coordinator.data.get("online", False)
        )
