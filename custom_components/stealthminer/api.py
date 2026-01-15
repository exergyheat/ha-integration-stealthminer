"""Stealthminer API Client."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    CMD_VERSION,
    CMD_SUMMARY,
    CMD_POWER,
    CMD_TEMPS,
    CMD_FANS,
    CMD_POOLS,
    CMD_PROFILES,
    CMD_ATM,
    CMD_CONFIG,
    CMD_DEVS,
    CMD_DEVDETAILS,
    CMD_TEMPCTRL,
    CMD_SESSION,
    CMD_LOGON,
    CMD_LOGOFF,
    CMD_ATMSET,
    CMD_CURTAIL,
    CMD_PROFILESET,
    CMD_REBOOTDEVICE,
    CMD_RESETMINER,
    CMD_POWERTARGETSET,
    CMD_LIMITS,
)

_LOGGER = logging.getLogger(__name__)


class StealthminerAPIError(Exception):
    """Stealthminer API Error."""


class StealthminerConnectionError(StealthminerAPIError):
    """Stealthminer Connection Error."""


class StealthminerSessionError(StealthminerAPIError):
    """Stealthminer Session Error."""


class StealthminerAPI:
    """Stealthminer API Client using HTTP API."""

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        timeout: int = DEFAULT_TIMEOUT,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the Stealthminer API client."""
        self._host = host
        self._port = port
        self._timeout = timeout
        self._session = session
        self._base_url = f"http://{host}:{port}/api"
        self._session_id: str | None = None

    @property
    def host(self) -> str:
        """Return the host."""
        return self._host

    @property
    def port(self) -> int:
        """Return the port."""
        return self._port

    async def _request(
        self,
        command: str,
        parameter: str | None = None,
    ) -> dict[str, Any]:
        """Make a request to the Stealthminer API."""
        payload: dict[str, str] = {"command": command}
        if parameter:
            payload["parameter"] = parameter

        headers = {"Content-Type": "application/json"}

        try:
            if self._session is None:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self._base_url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=self._timeout),
                    ) as response:
                        response.raise_for_status()
                        data = await response.json()
            else:
                async with self._session.post(
                    self._base_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self._timeout),
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

            # Check for API errors
            if "STATUS" in data and data["STATUS"]:
                status = data["STATUS"][0]
                if status.get("STATUS") == "E":
                    raise StealthminerAPIError(status.get("Msg", "Unknown API error"))

            return data

        except aiohttp.ClientConnectorError as err:
            raise StealthminerConnectionError(
                f"Cannot connect to {self._host}:{self._port}"
            ) from err
        except asyncio.TimeoutError as err:
            raise StealthminerConnectionError(
                f"Timeout connecting to {self._host}:{self._port}"
            ) from err
        except aiohttp.ClientError as err:
            raise StealthminerAPIError(f"API request failed: {err}") from err

    async def test_connection(self) -> dict[str, Any]:
        """Test the connection to the miner."""
        return await self.get_version()

    async def get_version(self) -> dict[str, Any]:
        """Get miner version info."""
        data = await self._request(CMD_VERSION)
        return data.get("VERSION", [{}])[0]

    async def get_summary(self) -> dict[str, Any]:
        """Get miner summary statistics."""
        data = await self._request(CMD_SUMMARY)
        return data.get("SUMMARY", [{}])[0]

    async def get_power(self) -> dict[str, Any]:
        """Get power consumption."""
        data = await self._request(CMD_POWER)
        return data.get("POWER", [{}])[0]

    async def get_temps(self) -> list[dict[str, Any]]:
        """Get temperature data."""
        data = await self._request(CMD_TEMPS)
        return data.get("TEMPS", [])

    async def get_fans(self) -> dict[str, Any]:
        """Get fan data."""
        data = await self._request(CMD_FANS)
        return {
            "fans": data.get("FANS", []),
            "fanctrl": data.get("FANCTRL", [{}])[0] if data.get("FANCTRL") else {},
        }

    async def get_pools(self) -> list[dict[str, Any]]:
        """Get pool configuration."""
        data = await self._request(CMD_POOLS)
        return data.get("POOLS", [])

    async def get_profiles(self) -> list[dict[str, Any]]:
        """Get available profiles."""
        data = await self._request(CMD_PROFILES)
        return data.get("PROFILES", [])

    async def get_atm(self) -> dict[str, Any]:
        """Get ATM configuration."""
        data = await self._request(CMD_ATM)
        return data.get("ATM", [{}])[0]

    async def get_config(self) -> dict[str, Any]:
        """Get miner configuration."""
        data = await self._request(CMD_CONFIG)
        return data.get("CONFIG", [{}])[0]

    async def get_devs(self) -> list[dict[str, Any]]:
        """Get device/board info."""
        data = await self._request(CMD_DEVS)
        return data.get("DEVS", [])

    async def get_devdetails(self) -> list[dict[str, Any]]:
        """Get device details."""
        data = await self._request(CMD_DEVDETAILS)
        return data.get("DEVDETAILS", [])

    async def get_tempctrl(self) -> dict[str, Any]:
        """Get temperature control settings."""
        data = await self._request(CMD_TEMPCTRL)
        return data.get("TEMPCTRL", [{}])[0]

    async def get_limits(self) -> dict[str, Any]:
        """Get miner parameter limits."""
        data = await self._request(CMD_LIMITS)
        return data.get("LIMITS", [{}])[0]

    async def get_session(self) -> str:
        """Get current session ID (empty if none)."""
        data = await self._request(CMD_SESSION)
        sessions = data.get("SESSION", [{}])
        return sessions[0].get("SessionID", "") if sessions else ""

    async def get_all_data(self) -> dict[str, Any]:
        """Get all data for coordinator update."""
        # Fetch all data concurrently
        results = await asyncio.gather(
            self.get_version(),
            self.get_summary(),
            self.get_power(),
            self.get_temps(),
            self.get_fans(),
            self.get_pools(),
            self.get_profiles(),
            self.get_atm(),
            self.get_config(),
            self.get_devs(),
            self.get_devdetails(),
            self.get_tempctrl(),
            return_exceptions=True,
        )

        # Process results
        data: dict[str, Any] = {"online": True}
        keys = [
            "version",
            "summary",
            "power",
            "temps",
            "fans",
            "pools",
            "profiles",
            "atm",
            "config",
            "devs",
            "devdetails",
            "tempctrl",
        ]

        for key, result in zip(keys, results):
            if isinstance(result, Exception):
                _LOGGER.warning("Error fetching %s: %s", key, result)
                data[key] = (
                    {}
                    if key not in ("temps", "pools", "profiles", "devs", "devdetails")
                    else []
                )
            else:
                data[key] = result

        return data

    # Session management for write operations
    async def _create_session(self) -> str:
        """Create a new session for write operations."""
        # First check if there's an existing session
        current = await self.get_session()
        if current:
            _LOGGER.warning("Session already exists: %s", current)
            raise StealthminerSessionError("Another session is active")

        data = await self._request(CMD_LOGON)
        sessions = data.get("SESSION", [{}])
        session_id = sessions[0].get("SessionID", "") if sessions else ""

        if not session_id:
            raise StealthminerSessionError("Failed to create session")

        self._session_id = session_id
        return session_id

    async def _close_session(self) -> None:
        """Close the current session."""
        if not self._session_id:
            return

        try:
            await self._request(CMD_LOGOFF, self._session_id)
        except StealthminerAPIError as err:
            _LOGGER.warning("Error closing session: %s", err)
        finally:
            self._session_id = None

    async def _execute_with_session(
        self,
        command: str,
        params: str = "",
    ) -> dict[str, Any]:
        """Execute a command that requires a session."""
        try:
            session_id = await self._create_session()
            full_params = f"{session_id},{params}" if params else session_id
            result = await self._request(command, full_params)
            return result
        finally:
            await self._close_session()

    # Control methods
    async def set_atm(self, enabled: bool) -> dict[str, Any]:
        """Enable or disable ATM."""
        enabled_str = "true" if enabled else "false"
        return await self._execute_with_session(CMD_ATMSET, f"enabled={enabled_str}")

    async def curtail_sleep(self) -> dict[str, Any]:
        """Put miner to sleep (curtail)."""
        return await self._execute_with_session(CMD_CURTAIL, "sleep")

    async def curtail_wakeup(self, mode: str = "safe") -> dict[str, Any]:
        """Wake up miner from curtailment."""
        return await self._execute_with_session(CMD_CURTAIL, f"wakeup,mode={mode}")

    async def set_profile(self, profile_name: str, board: int = 0) -> dict[str, Any]:
        """Set the mining profile."""
        return await self._execute_with_session(CMD_PROFILESET, f"{board},{profile_name}")

    async def reboot(self) -> dict[str, Any]:
        """Reboot the miner."""
        return await self._execute_with_session(CMD_REBOOTDEVICE)

    async def reset_miner(self) -> dict[str, Any]:
        """Reset the miner application."""
        return await self._execute_with_session(CMD_RESETMINER)

    async def set_power_target(self, power: int) -> dict[str, Any]:
        """Set the power target in watts.

        When using power targeting, the miner's ATM automatically finds
        the best voltage and frequency combination within the desired power limit.
        """
        return await self._execute_with_session(CMD_POWERTARGETSET, f"power={power}")
