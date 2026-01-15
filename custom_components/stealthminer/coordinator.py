"""DataUpdateCoordinator for Stealthminer."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import StealthminerAPI, StealthminerAPIError, StealthminerConnectionError
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class StealthminerDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Stealthminer data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        api: StealthminerAPI,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self._device_info: dict[str, Any] = {}

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info for the miner."""
        return self._device_info

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the Stealthminer API."""
        try:
            data = await self.api.get_all_data()

            # Fetch limits separately (less frequent, but needed for UI)
            try:
                data["limits"] = await self.api.get_limits()
            except StealthminerAPIError:
                data["limits"] = {}

            # Update device info
            self._update_device_info(data)

            # Add computed values
            data = self._add_computed_values(data)

            return data

        except StealthminerConnectionError as err:
            # Return offline state instead of failing completely
            _LOGGER.warning("Connection error: %s", err)
            return {"online": False}
        except StealthminerAPIError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    def _update_device_info(self, data: dict[str, Any]) -> None:
        """Update device info from fetched data."""
        version = data.get("version", {})
        config = data.get("config", {})
        devdetails = data.get("devdetails", [{}])
        devdetail = devdetails[0] if devdetails else {}

        model = version.get("Type", config.get("Model", "Stealthminer"))
        hostname = config.get("Hostname", self.api.host)
        serial = devdetail.get("SerialNumber", config.get("SerialNumber", ""))
        sw_version = version.get("LUXminer", "")

        self._device_info = {
            "identifiers": {(DOMAIN, f"{self.api.host}:{self.api.port}")},
            "name": hostname,
            "manufacturer": "Luxor Technology",
            "model": model,
            "sw_version": sw_version,
            "configuration_url": f"http://{self.api.host}",
        }

        if serial:
            self._device_info["serial_number"] = serial

    def _add_computed_values(self, data: dict[str, Any]) -> dict[str, Any]:
        """Add computed values to the data."""
        summary = data.get("summary", {})
        power = data.get("power", {})
        temps = data.get("temps", [])
        fans_data = data.get("fans", {})
        fans = fans_data.get("fans", []) if isinstance(fans_data, dict) else []
        pools = data.get("pools", [])
        devs = data.get("devs", [])

        # Efficiency calculation (W/TH)
        watts = power.get("Watts", 0)
        hashrate_ghs = summary.get("GHS 5s", 0)
        hashrate_ths = hashrate_ghs / 1000 if hashrate_ghs else 0

        if hashrate_ths > 0 and watts > 0:
            data["efficiency"] = round(watts / hashrate_ths, 2)
        else:
            data["efficiency"] = None

        # Max board temperature
        if temps:
            all_temps = []
            for temp in temps:
                for key in [
                    "TopLeft",
                    "TopRight",
                    "BottomLeft",
                    "BottomRight",
                    "Board",
                    "Chip",
                ]:
                    if key in temp and temp[key] is not None:
                        all_temps.append(temp[key])
            data["temp_board_max"] = max(all_temps) if all_temps else None
        else:
            data["temp_board_max"] = None

        # Average fan speed and RPM
        if fans:
            speeds = [f.get("Speed", 0) for f in fans if "Speed" in f]
            rpms = [f.get("RPM", 0) for f in fans if "RPM" in f]
            data["fan_speed_avg"] = round(sum(speeds) / len(speeds)) if speeds else None
            data["fan_rpm_avg"] = round(sum(rpms) / len(rpms)) if rpms else None
        else:
            data["fan_speed_avg"] = None
            data["fan_rpm_avg"] = None

        # Active pool info
        active_pool = None
        for pool in pools:
            if pool.get("Status") == "Alive" and pool.get("Stratum Active"):
                active_pool = pool
                break

        if active_pool is None and pools:
            # Fall back to first pool
            active_pool = pools[0]

        if active_pool:
            data["active_pool_url"] = active_pool.get("Stratum URL", "")
            data["active_pool_user"] = active_pool.get("User", "")
            data["active_pool_difficulty"] = active_pool.get("Stratum Difficulty", 0)
            data["pool_connected"] = active_pool.get("Status") == "Alive"
        else:
            data["active_pool_url"] = None
            data["active_pool_user"] = None
            data["active_pool_difficulty"] = None
            data["pool_connected"] = False

        # Board count
        data["board_count"] = len(devs) if devs else 0

        return data

    def get_value(self, path: str) -> Any:
        """Get a value from data using dot notation path."""
        if not self.data:
            return None

        keys = path.split(".")
        value = self.data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            elif isinstance(value, list) and value:
                # For lists, get from first item
                value = value[0].get(key) if isinstance(value[0], dict) else None
            else:
                return None

            if value is None:
                return None

        return value

    def get_computed_value(self, key: str) -> Any:
        """Get a computed value from data."""
        if not self.data:
            return None
        return self.data.get(key)
