# Winix Air Purifiers

[![HACS](https://img.shields.io/badge/HACS-Custom-orange?style=for-the-badge)](https://hacs.xyz)
[![GitHub Release](https://img.shields.io/github/v/release/regaw-leinad/homeassistant-winix-purifiers?style=for-the-badge)](https://github.com/regaw-leinad/homeassistant-winix-purifiers/releases)

[Home Assistant](https://www.home-assistant.io) custom integration for [Winix](https://www.winixamerica.com) air purifiers, built by the maintainer of [homebridge-winix-purifiers](https://github.com/regaw-leinad/homebridge-winix-purifiers) and [winix-api](https://github.com/regaw-leinad/winix-api).

## Features

- **Dynamic Device Discovery**: Automatically discovers all Winix purifiers linked to your account.
- **Fan Control**: Power on/off, fan speed (Low, Medium, High, Turbo), and preset modes (Auto, Sleep).
- **PlasmaWave**: Independent switch for PlasmaWave ionizer control, separate from fan modes.
- **Air Quality Sensor**: AQI sensor with support for 3-level (C545) and 4-level (Tower XQ) reporting.
- **PM2.5 Sensor**: Real-time particulate matter readings on supported models.
- **Ambient Light Sensor**: Light level reporting on supported models.
- **Filter Life Tracking**: Filter life percentage with a replacement alert when it's time to change the filter.
- **Model-Specific Features**: Brightness control (C610+), child lock (C610+), power-off timer (Tower XQ).
- **Optimistic Updates**: UI reflects changes immediately without waiting for the next poll cycle.
- **Encrypted API Communication**: AES-256-CBC encryption for all sensitive API calls.
- **Automatic Token Refresh**: Seamlessly refreshes authentication in the background.

## Device Support

This integration supports Winix air purifiers. Features are automatically detected from each device's reported attributes, so any model should work out of the box.

Known models and their features:

| Model | PlasmaWave | Brightness | Child Lock | Timer | Pollution Lamp |
|-------|------------|------------|------------|-------|----------------|
| C545 | Yes | - | - | - | - |
| C610 | Yes | Yes | Yes | - | - |
| C909 | Yes | - | - | - | - |
| 5510 / 5520 | Yes | - | - | - | - |
| 9800 | Yes | - | - | - | - |
| AM90 | Yes | - | - | - | - |
| T500 | Yes | - | - | - | - |
| T810 / T830 | Yes | Yes | - | - | - |
| T1000 | - | - | Yes | - | - |
| Tower XQ / XQ PRO | Yes | - | Yes | Yes | Yes |
| HR1000 | Yes | - | Yes | Yes | Yes |
| NK105 | Yes | - | - | - | Yes |
| T1 | Yes | - | - | Yes | - |
| ZERO+ | Yes | - | Yes | Yes | - |
| TITAN | Yes | - | - | Yes | - |
| XLC | Yes | - | - | - | - |
| MASTER(S) | - | - | Yes | Yes | - |

All models also support: power, mode (auto/manual), fan speed, AQI, and filter life tracking.

Additional models (T800, WXAP800, ZERO 360, ZERO+, and others) are also supported. All features are detected automatically from the device, so even models not listed here should work.

Some models also report ambient light, PM2.5 density, filter door status, and filter presence detection. These sensors are automatically created when the device reports them.

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant.
2. Go to **Integrations** and click the three dots menu in the top right.
3. Select **Custom repositories**.
4. Add `https://github.com/regaw-leinad/homeassistant-winix-purifiers` with category **Integration**.
5. Search for "Winix Air Purifiers" and install it.
6. Restart Home Assistant.

### Manual

1. Copy the `custom_components/winix_purifiers` directory into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## Setup

1. Go to **Settings > Devices & Services > Add Integration**.
2. Search for "Winix Air Purifiers".
3. Enter your Winix app email and password.
4. Your devices will be automatically discovered.

### Alternate Winix Account

Winix's system limits users to a single active session per account. If the same account is used on both the Winix app and Home Assistant, you may get logged out of one. To avoid this, create a second Winix account and share your devices to it via the Winix app.

## Entities

Each purifier exposes the following entities:

### Controls
- **Fan**: Power, speed control (4 levels), preset modes (Auto, Sleep)
- **PlasmaWave**: Independent on/off switch

### Sensors
- **Air Quality**: AQI index value (25 = Good, 75 = Fair, 150 = Poor, 200 = Very Poor)
- **Ambient Light**: Illuminance in lux (model-dependent)
- **PM2.5**: Particulate matter in ug/m3 (model-dependent)

### Diagnostics
- **Filter Life**: Remaining filter life percentage
- **Filter Replacement**: Problem indicator when filter life is below 10%

### Configuration (model-dependent)
- **Display Brightness**: Off, Low, Medium, High (C610+)
- **Child Lock**: On/off (C610+)
- **Timer**: Power-off timer (Tower XQ)

## Acknowledgments

- [winix-api](https://github.com/regaw-leinad/winix-api) - The TypeScript Winix API library this integration is based on.
- [homebridge-winix-purifiers](https://github.com/regaw-leinad/homebridge-winix-purifiers) - The Homebridge plugin that inspired this integration's architecture.
