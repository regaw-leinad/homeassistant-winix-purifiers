# Winix Air Purifiers

[![HACS](https://img.shields.io/badge/HACS-Custom-orange?style=for-the-badge)](https://hacs.xyz)
[![GitHub Release](https://img.shields.io/github/v/release/regaw-leinad/homeassistant-winix-purifiers?style=for-the-badge)](https://github.com/regaw-leinad/homeassistant-winix-purifiers/releases)

[Home Assistant](https://www.home-assistant.io) custom integration for [Winix](https://www.winixamerica.com) air purifiers, built by the maintainer of [homebridge-winix-purifiers](https://github.com/regaw-leinad/homebridge-winix-purifiers) and [winix-api](https://github.com/regaw-leinad/winix-api).

## Table of Contents

* [Features](#features)
* [Device Support](#device-support)
* [Installation](#installation)
* [Setup](#setup)
* [Entities](#entities)
* [FAQ](#faq)
* [Acknowledgments](#acknowledgments)

## Features

- **Dynamic Device Discovery**: Automatically discovers all Winix purifiers linked to your account.
- **Fan Control**: Power on/off, fan speed (Low, Medium, High, Turbo), and preset modes (Auto, Sleep).
- **PlasmaWave**: Independent switch for PlasmaWave ionizer control, separate from fan modes.
- **Air Quality Sensor**: AQI sensor with support for 3-level (C545) and 4-level (Tower XQ) reporting.
- **PM2.5 Sensor**: Real-time particulate matter readings on supported models.
- **Ambient Light Sensor**: Light level reporting on supported models.
- **Filter Life Tracking**: Filter life percentage with a replacement alert when it's time to change the filter.
- **Model-Specific Features**: Brightness control, child lock, power-off timer, pollution lamp, and UV sterilization.
- **Optimistic Updates**: UI reflects changes immediately without waiting for the next poll cycle.
- **Encrypted API Communication**: AES-256-CBC encryption for all sensitive API calls.
- **Automatic Token Refresh**: Seamlessly refreshes authentication in the background.

<details>
<summary><h3>Device Support</h3></summary>

This integration supports Winix air purifiers. Features are automatically detected from each device's reported attributes, so any model should work out of the box.

Known models and their features:

| Model | PlasmaWave | Brightness | Child Lock | Timer | Pollution Lamp |
|-------|------------|------------|------------|-------|----------------|
| C5 | Yes | - | - | - | - |
| C545 | Yes | - | - | - | - |
| C610 | Yes | Yes | Yes | - | - |
| C909 | Yes | - | - | - | - |
| 5510 / 5520 | Yes | - | - | - | - |
| 9800 | Yes | - | - | - | - |
| AM90 | Yes | - | - | - | - |
| T500 | Yes | - | - | - | - |
| T800 | Yes | Yes | - | - | - |
| T810 / T830 | Yes | Yes | - | - | - |
| T1000 | - | - | Yes | - | - |
| Tower Q | Yes | - | - | - | - |
| Tower Prime | - | - | - | - | - |
| Tower Prime+ | - | - | Yes | - | - |
| Tower XQ / XQ PRO | Yes | - | Yes | Yes | Yes |
| HR1000 | Yes | - | Yes | Yes | Yes |
| NK105 | Yes | - | - | - | Yes |
| T1 | Yes | - | - | Yes | - |
| WXAP800 | Yes | Yes | - | - | - |
| ZERO 360 | Yes | Yes | - | - | - |
| ZERO+ | Yes | - | Yes | Yes | - |
| TITAN | Yes | - | - | Yes | - |
| XLC | Yes | - | - | - | - |
| MASTER(S) | - | - | Yes | Yes | - |

All models also support: power, mode (auto/manual), fan speed, AQI, and filter life tracking.

All features are detected automatically from the device, so even models not listed here should work. Some models also report ambient light, PM2.5 density, filter door status, and filter presence detection. These sensors are automatically created when the device reports them.

</details>

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

<details>
<summary><h3>Entities</h3></summary>

Each purifier exposes the following entities:

### Controls
- **Fan**: Power, speed control (4 levels), preset modes (Auto, Sleep)
- **PlasmaWave**: Independent on/off switch

### Sensors
- **Air Quality**: AQI index value (25 = Good, 75 = Fair, 150 = Poor, 200 = Very Poor)
- **Ambient Light**: Illuminance in lux (model-dependent)
- **PM2.5**: Particulate matter in µg/m³ (model-dependent)

### Diagnostics
- **Filter Life**: Remaining filter life percentage
- **Filter Replacement**: Problem indicator when filter life is below threshold
- **Filter Door**: Door open/closed status (model-dependent)
- **Filter Missing**: Alert when filter is not detected (model-dependent)

### Configuration (model-dependent)
- **Display Brightness**: Off, Low, Medium, High
- **Child Lock**: On/off
- **Timer**: Power-off timer (Off, 1h, 2h, 4h, 8h, 12h)
- **Pollution Lamp**: AQI indicator LED on/off
- **UV Sterilization**: On/off

</details>

## FAQ

### Do I need a separate Winix account?

**Strongly recommended.** Winix's system limits users to a single active session per account. If the same account is used on both the Winix app and Home Assistant, one session will get logged out, causing frequent authentication disruptions.

_**Yes, this is an annoying and tedious one-time setup, but it is well worth not having to continually fix authentication issues.**_

To set this up:

1. Create a new Winix account (use a different email).
2. In the Winix app, share your devices from your primary account to the new account.
3. Use the new account credentials when setting up this integration.

### My devices aren't responding / showing as unavailable?

This is likely a session conflict. See the [alternate account FAQ](#do-i-need-a-separate-winix-account) above. If you're already using a dedicated account, try removing and re-adding the integration to force a fresh login.

### How often does the integration poll for updates?

By default, every 30 seconds. You can adjust this in the integration's options (**Settings > Devices & Services > Winix Air Purifiers > Configure**). The minimum is 15 seconds. Control commands (power, speed, etc.) use optimistic updates, so the UI reflects changes immediately.

## Acknowledgments

- [winix-api](https://github.com/regaw-leinad/winix-api) - The TypeScript Winix API library this integration is based on.
- [homebridge-winix-purifiers](https://github.com/regaw-leinad/homebridge-winix-purifiers) - The Homebridge plugin that inspired this integration's architecture.
