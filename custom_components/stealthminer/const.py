"""Constants for the Exergy - Stealthminer integration."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "stealthminer"

# Configuration
CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_SCAN_INTERVAL: Final = "scan_interval"

# Defaults
DEFAULT_PORT: Final = 8080
DEFAULT_SCAN_INTERVAL: Final = 30
DEFAULT_TIMEOUT: Final = 10

# API Commands
CMD_VERSION: Final = "version"
CMD_SUMMARY: Final = "summary"
CMD_POWER: Final = "power"
CMD_TEMPS: Final = "temps"
CMD_FANS: Final = "fans"
CMD_POOLS: Final = "pools"
CMD_PROFILES: Final = "profiles"
CMD_ATM: Final = "atm"
CMD_CONFIG: Final = "config"
CMD_DEVS: Final = "devs"
CMD_DEVDETAILS: Final = "devdetails"
CMD_TEMPCTRL: Final = "tempctrl"
CMD_SESSION: Final = "session"
CMD_LOGON: Final = "logon"
CMD_LOGOFF: Final = "logoff"
CMD_ATMSET: Final = "atmset"
CMD_CURTAIL: Final = "curtail"
CMD_PROFILESET: Final = "profileset"
CMD_REBOOTDEVICE: Final = "rebootdevice"
CMD_RESETMINER: Final = "resetminer"
CMD_POWERTARGETSET: Final = "powertargetset"
CMD_LIMITS: Final = "limits"

# Units
UNIT_TERAHASH: Final = "TH/s"
UNIT_GIGAHASH: Final = "GH/s"
UNIT_WATTS_PER_TERAHASH: Final = "W/TH"
UNIT_RPM: Final = "RPM"

# Platforms
PLATFORMS: Final = [
    "sensor",
    "binary_sensor",
    "switch",
    "button",
    "select",
    "number",
]
