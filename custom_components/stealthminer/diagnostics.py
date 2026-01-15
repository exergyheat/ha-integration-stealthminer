"""Diagnostics support for Stealthminer."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import StealthminerDataUpdateCoordinator

TO_REDACT = {
    CONF_HOST,
    "host",
    "ip",
    "hostname",
    "Hostname",
    "IP",
    "User",
    "user",
    "password",
    "token",
    "api_key",
    "secret",
    "SerialNumber",
    "serial_number",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: StealthminerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    diagnostics_data = {
        "entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "domain": entry.domain,
            "title": entry.title,
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": async_redact_data(entry.options, TO_REDACT),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "data": async_redact_data(coordinator.data, TO_REDACT)
            if coordinator.data
            else None,
        },
    }

    return diagnostics_data
