# Exergy - Stealthminer

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/exergyheat/ha-integration-stealthminer.svg)](https://github.com/exergyheat/ha-integration-stealthminer/releases)
[![License](https://img.shields.io/github/license/exergyheat/ha-integration-stealthminer.svg)]

Home Assistant custom integration for monitoring and controlling Bitcoin miners running LuxOS firmware.

## Features

- **Real-time Monitoring**
  - Hashrate (5s, 1m, 15m, 30m, average)
  - Power consumption and efficiency (W/TH)
  - Board and chip temperatures
  - Fan speed and RPM
  - Pool connection status
  - Share statistics (accepted, rejected, stale)

- **Controls**
  - ATM (Auto-Tuning Mode) toggle
  - Sleep mode / Wake up
  - Profile selection
  - Power limit control with adaptive control loop
  - Reboot and reset buttons

- **Diagnostics**
  - System status
  - LuxOS version
  - Board and chip count
  - Curtail mode status

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu in the top right
3. Select "Custom repositories"
4. Add this repository URL: `https://github.com/exergyheat/ha-integration-stealthminer`
5. Select "Integration" as the category
6. Click "Add"
7. Search for "Stealthminer" and install it
8. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/exergyheat/ha-integration-stealthminer/releases)
2. Extract and copy the `custom_components/stealthminer` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Stealthminer"
4. Enter your miner's IP address and port (default: 4028)
5. Click **Submit**

## Requirements

- Home Assistant 2024.1.0 or newer
- Miner running LuxOS firmware with HTTP API enabled (port 4028)

## Entities

### Sensors
| Entity | Description |
|--------|-------------|
| Hashrate (5s/1m/15m/30m/avg) | Mining hashrate at various intervals |
| Power | Current power consumption in watts |
| Efficiency | Power efficiency in W/TH |
| Board Temperature | Maximum board temperature |
| Fan Speed | Average fan speed percentage |
| Fan RPM | Average fan RPM |
| Accepted/Rejected/Stale Shares | Share statistics |
| Active Pool | Currently connected pool URL |
| Current Profile | Active mining profile |
| System Status | Miner operational status |

### Binary Sensors
| Entity | Description |
|--------|-------------|
| Miner Online | Connection status |
| Pool Connected | Pool connection status |
| ATM Enabled | Auto-Tuning Mode status |
| Is Mining | Whether the miner is actively mining |

### Controls
| Entity | Description |
|--------|-------------|
| ATM Switch | Enable/disable Auto-Tuning Mode |
| Sleep Mode Switch | Put miner to sleep / wake up |
| Profile Select | Choose mining profile |
| Power Limit | Set target power consumption |
| Reboot Button | Reboot the miner |
| Reset Miner Button | Reset the miner application |
| Wake Up Button | Wake the miner from sleep |

## Support

If you encounter any issues, please [open an issue](https://github.com/exergyheat/ha-integration-stealthminer/issues) on GitHub.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
