"""Config flow for Exergy - Stealthminer integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import StealthminerAPI, StealthminerAPIError, StealthminerConnectionError
from .const import (
    DOMAIN,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    CONF_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


class StealthminerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Exergy - Stealthminer."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._host: str | None = None
        self._port: int = DEFAULT_PORT
        self._miner_info: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._port = user_input.get(CONF_PORT, DEFAULT_PORT)

            # Test connection
            session = async_get_clientsession(self.hass)
            api = StealthminerAPI(
                host=self._host,
                port=self._port,
                session=session,
            )

            try:
                version_info = await api.test_connection()
                config_info = await api.get_config()

                self._miner_info = {
                    "model": version_info.get("Type", "Stealthminer"),
                    "hostname": config_info.get("Hostname", self._host),
                    "version": version_info.get("LUXminer", ""),
                }

            except StealthminerConnectionError:
                errors["base"] = "cannot_connect"
            except StealthminerAPIError:
                errors["base"] = "api_error"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if not errors:
                # Check if already configured
                await self.async_set_unique_id(f"{self._host}:{self._port}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=self._miner_info.get("hostname", self._host),
                    data={
                        CONF_HOST: self._host,
                        CONF_PORT: self._port,
                    },
                    options={
                        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> StealthminerOptionsFlowHandler:
        """Get the options flow for this handler."""
        return StealthminerOptionsFlowHandler(config_entry)


class StealthminerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Stealthminer options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
                }
            ),
        )
