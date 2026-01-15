"""Sensor platform for Exergy - Stealthminer."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfFrequency,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, UNIT_TERAHASH, UNIT_WATTS_PER_TERAHASH, UNIT_RPM
from .coordinator import StealthminerDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


# Sensor definitions: (key, name, unit, device_class, state_class, icon, value_path, value_fn, entity_category, enabled_default)
SENSOR_TYPES: list[tuple] = [
    # Hashrate sensors
    ("hashrate_5s", "Hashrate (5s)", UNIT_TERAHASH, None, SensorStateClass.MEASUREMENT, "mdi:pickaxe", "summary.GHS 5s", None, None, True),
    ("hashrate_1m", "Hashrate (1m)", UNIT_TERAHASH, None, SensorStateClass.MEASUREMENT, "mdi:pickaxe", "summary.GHS 1m", None, None, True),
    ("hashrate_15m", "Hashrate (15m)", UNIT_TERAHASH, None, SensorStateClass.MEASUREMENT, "mdi:pickaxe", "summary.GHS 15m", None, None, True),
    ("hashrate_30m", "Hashrate (30m)", UNIT_TERAHASH, None, SensorStateClass.MEASUREMENT, "mdi:pickaxe", "summary.GHS 30m", None, None, True),
    ("hashrate_avg", "Hashrate (Average)", UNIT_TERAHASH, None, SensorStateClass.MEASUREMENT, "mdi:pickaxe", "summary.GHS av", None, None, True),
    # Power
    ("power", "Power", UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, None, "power.Watts", None, None, True),
    ("efficiency", "Efficiency", UNIT_WATTS_PER_TERAHASH, None, SensorStateClass.MEASUREMENT, "mdi:lightning-bolt", None, "efficiency", None, True),
    # Shares
    ("accepted_shares", "Accepted Shares", None, None, SensorStateClass.TOTAL_INCREASING, "mdi:check-circle", "summary.Accepted", None, None, True),
    ("rejected_shares", "Rejected Shares", None, None, SensorStateClass.TOTAL_INCREASING, "mdi:close-circle", "summary.Rejected", None, None, True),
    ("stale_shares", "Stale Shares", None, None, SensorStateClass.TOTAL_INCREASING, "mdi:clock-alert", "summary.Stale", None, None, True),
    ("hardware_errors", "Hardware Errors", None, None, SensorStateClass.TOTAL_INCREASING, "mdi:alert-circle", "summary.Hardware Errors", None, None, True),
    ("best_share", "Best Share", None, None, None, "mdi:trophy", "summary.Best Share", None, EntityCategory.DIAGNOSTIC, True),
    # Uptime
    ("uptime", "Uptime", UnitOfTime.SECONDS, SensorDeviceClass.DURATION, SensorStateClass.TOTAL_INCREASING, None, "summary.Elapsed", None, EntityCategory.DIAGNOSTIC, True),
    # Temperature sensors
    ("temp_board_max", "Board Temperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None, None, "temp_board_max", None, True),
    ("temp_exhaust_top", "Exhaust Temperature (Top)", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None, "temps.TopLeft", None, None, False),
    ("temp_intake_top", "Intake Temperature (Top)", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None, "temps.TopRight", None, None, False),
    ("temp_exhaust_bottom", "Exhaust Temperature (Bottom)", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None, "temps.BottomLeft", None, None, False),
    ("temp_intake_bottom", "Intake Temperature (Bottom)", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None, "temps.BottomRight", None, None, False),
    ("temp_target", "Target Temperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, None, "mdi:thermometer-check", "tempctrl.Target", None, EntityCategory.DIAGNOSTIC, True),
    # Fan sensors
    ("fan_speed_avg", "Fan Speed", PERCENTAGE, None, SensorStateClass.MEASUREMENT, "mdi:fan", None, "fan_speed_avg", None, True),
    ("fan_rpm_avg", "Fan RPM", UNIT_RPM, None, SensorStateClass.MEASUREMENT, "mdi:fan", None, "fan_rpm_avg", None, True),
    # Profile and frequency
    ("current_profile", "Current Profile", None, None, None, "mdi:tune", "config.Profile", None, None, True),
    ("frequency", "Frequency", UnitOfFrequency.MEGAHERTZ, SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, None, "devdetails.Frequency", None, EntityCategory.DIAGNOSTIC, True),
    ("voltage", "Voltage", "V", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, None, "devdetails.Voltage", None, EntityCategory.DIAGNOSTIC, True),
    # Pool info
    ("pool_url", "Active Pool", None, None, None, "mdi:server-network", None, "active_pool_url", None, True),
    ("pool_user", "Pool User", None, None, None, "mdi:account", None, "active_pool_user", EntityCategory.DIAGNOSTIC, True),
    ("pool_difficulty", "Pool Difficulty", None, None, None, "mdi:gauge", None, "active_pool_difficulty", EntityCategory.DIAGNOSTIC, True),
    # System info
    ("system_status", "System Status", None, None, None, "mdi:information", "config.SystemStatus", None, None, True),
    ("curtail_mode", "Curtail Mode", None, None, None, "mdi:sleep", "config.CurtailMode", None, EntityCategory.DIAGNOSTIC, True),
    ("luxos_version", "LuxOS Version", None, None, None, "mdi:tag", "version.LUXminer", None, EntityCategory.DIAGNOSTIC, True),
    ("board_count", "Board Count", None, None, None, "mdi:developer-board", None, "board_count", EntityCategory.DIAGNOSTIC, True),
    ("chip_count", "Chip Count", None, None, None, "mdi:chip", "devdetails.Chips", None, EntityCategory.DIAGNOSTIC, True),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Stealthminer sensors from a config entry."""
    coordinator: StealthminerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for sensor_type in SENSOR_TYPES:
        key, name, unit, device_class, state_class, icon, value_path, value_fn, entity_category, enabled_default = sensor_type
        entities.append(
            StealthminerSensor(
                coordinator=coordinator,
                key=key,
                name=name,
                unit=unit,
                device_class=device_class,
                state_class=state_class,
                icon=icon,
                value_path=value_path,
                value_fn=value_fn,
                entity_category=entity_category,
                enabled_default=enabled_default,
            )
        )

    async_add_entities(entities)


class StealthminerSensor(CoordinatorEntity[StealthminerDataUpdateCoordinator], SensorEntity):
    """Representation of a Stealthminer sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: StealthminerDataUpdateCoordinator,
        key: str,
        name: str,
        unit: str | None,
        device_class: SensorDeviceClass | None,
        state_class: SensorStateClass | None,
        icon: str | None,
        value_path: str | None,
        value_fn: str | None,
        entity_category: EntityCategory | None,
        enabled_default: bool,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._value_path = value_path
        self._value_fn = value_fn

        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_icon = icon
        self._attr_entity_category = entity_category
        self._attr_entity_registry_enabled_default = enabled_default
        self._attr_unique_id = f"{coordinator.api.host}_{coordinator.api.port}_{key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self.coordinator.data or not self.coordinator.data.get("online", False):
            return None

        # Handle computed values
        if self._value_fn:
            return self._get_computed_value(self._value_fn)

        # Handle path-based values
        if self._value_path:
            value = self._get_path_value(self._value_path)

            # Convert hashrate from GH/s to TH/s
            if self._key.startswith("hashrate_") and value is not None:
                return round(value / 1000, 2)

            return value

        return None

    def _get_path_value(self, path: str) -> Any:
        """Get value from data using dot notation path."""
        keys = path.split(".")
        data = self.coordinator.data

        for key in keys:
            if isinstance(data, dict):
                data = data.get(key)
            elif isinstance(data, list) and data:
                # Get from first item in list
                data = data[0].get(key) if isinstance(data[0], dict) else None
            else:
                return None

            if data is None:
                return None

        return data

    def _get_computed_value(self, key: str) -> Any:
        """Get a computed value."""
        data = self.coordinator.data

        if key == "efficiency":
            return data.get("efficiency")
        if key == "temp_board_max":
            return data.get("temp_board_max")
        if key == "fan_speed_avg":
            return data.get("fan_speed_avg")
        if key == "fan_rpm_avg":
            return data.get("fan_rpm_avg")
        if key == "active_pool_url":
            return data.get("active_pool_url")
        if key == "active_pool_user":
            return data.get("active_pool_user")
        if key == "active_pool_difficulty":
            return data.get("active_pool_difficulty")
        if key == "board_count":
            return data.get("board_count")

        return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.coordinator.data.get("online", False)
        )
