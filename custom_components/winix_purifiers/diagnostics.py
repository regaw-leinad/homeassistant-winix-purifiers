"""Diagnostics for Winix Purifiers."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from .const import DOMAIN
from .coordinator import WinixDeviceCoordinator

REDACT_KEYS = {
    "username",
    "password",
    "refresh_token",
    "user_id",
    "access_token",
    "mac",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinators: dict[str, WinixDeviceCoordinator] = hass.data[DOMAIN][entry.entry_id]

    devices_data = {}
    for device_id, coordinator in coordinators.items():
        device_data = coordinator.data
        devices_data[device_id] = {
            "model": device_data.info.model_name,
            "alias": device_data.info.device_alias,
            "mac": device_data.info.mac,
            "mcu_ver": device_data.info.mcu_ver,
            "capabilities": {
                "has_brightness": device_data.capabilities.has_brightness,
                "has_child_lock": device_data.capabilities.has_child_lock,
                "has_ambient_light": device_data.capabilities.has_ambient_light,
                "has_pm25": device_data.capabilities.has_pm25,
                "has_timer": device_data.capabilities.has_timer,
            },
            "status": {
                "power": device_data.status.power,
                "mode": device_data.status.mode,
                "airflow": device_data.status.airflow,
                "air_quality": device_data.status.air_quality,
                "air_qvalue": device_data.status.air_qvalue,
                "plasmawave": device_data.status.plasmawave,
                "filter_hours": device_data.status.filter_hours,
                "ambient_light": device_data.status.ambient_light,
                "pm25": device_data.status.pm25,
            },
            "consecutive_failures": device_data.consecutive_failures,
            "has_received_data": device_data.has_received_data,
        }

    return async_redact_data(
        {
            "config_entry": async_redact_data(dict(entry.data), REDACT_KEYS),
            "devices": devices_data,
        },
        REDACT_KEYS,
    )
