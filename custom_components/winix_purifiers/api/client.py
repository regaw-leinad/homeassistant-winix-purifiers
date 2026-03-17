"""Winix device control and status API client."""

from __future__ import annotations

import logging

import aiohttp

from .const import URL_DEVICE_CONTROL, URL_DEVICE_STATUS
from .device import (
    Airflow,
    AirQuality,
    Attribute,
    DeviceStatus,
    Mode,
    Plasmawave,
    Power,
)
from .exceptions import WinixApiError

_LOGGER = logging.getLogger(__name__)

# Known air quality enum values
_AIR_QUALITY_VALUES = {
    AirQuality.GOOD,
    AirQuality.FAIR,
    AirQuality.POOR,
    AirQuality.VERY_POOR,
}


class WinixDeviceClient:
    """Controls a single Winix device via the unauthenticated IoT API."""

    def __init__(self, session: aiohttp.ClientSession, device_id: str) -> None:
        self._session = session
        self._device_id = device_id

    @property
    def device_id(self) -> str:
        return self._device_id

    async def get_status(self) -> DeviceStatus:
        """Fetch the current device status."""
        attrs = await self._get_status_attributes()

        return DeviceStatus(
            power=Power(attrs.get(Attribute.POWER, Power.OFF)),
            mode=Mode(attrs.get(Attribute.MODE, Mode.AUTO)),
            airflow=Airflow(attrs.get(Attribute.AIRFLOW, Airflow.LOW)),
            air_quality=self._parse_air_quality(attrs),
            plasmawave=Plasmawave(attrs.get(Attribute.PLASMAWAVE, Plasmawave.OFF)),
            filter_hours=self._parse_int(attrs.get(Attribute.FILTER_HOURS), 0),
            air_qvalue=self._parse_int_optional(attrs.get(Attribute.AIR_QVALUE)),
            ambient_light=self._parse_int_optional(attrs.get(Attribute.AMBIENT_LIGHT)),
            pm25=self._parse_int_optional(attrs.get(Attribute.PM25)),
            timer=self._parse_int_optional(attrs.get(Attribute.TIMER)),
            child_lock=attrs.get(Attribute.CHILD_LOCK),
            brightness=attrs.get(Attribute.BRIGHTNESS),
        )

    async def get_raw_attributes(self) -> dict[str, str]:
        """Fetch raw attributes dict (for capability detection on first poll)."""
        return await self._get_status_attributes()

    async def set_power(self, value: Power) -> None:
        """Set device power state."""
        _LOGGER.debug("client:set_power(%s) device=%s", value, self._device_id)
        await self._set_attribute(Attribute.POWER, value)

    async def set_mode(self, value: Mode) -> None:
        """Set device mode (auto/manual)."""
        _LOGGER.debug("client:set_mode(%s) device=%s", value, self._device_id)
        await self._set_attribute(Attribute.MODE, value)

    async def set_airflow(self, value: Airflow) -> None:
        """Set fan airflow speed."""
        _LOGGER.debug("client:set_airflow(%s) device=%s", value, self._device_id)
        await self._set_attribute(Attribute.AIRFLOW, value)

    async def set_plasmawave(self, value: Plasmawave) -> None:
        """Set plasmawave state."""
        _LOGGER.debug("client:set_plasmawave(%s) device=%s", value, self._device_id)
        await self._set_attribute(Attribute.PLASMAWAVE, value)

    async def set_brightness(self, value: str) -> None:
        """Set display brightness (C610+)."""
        _LOGGER.debug("client:set_brightness(%s) device=%s", value, self._device_id)
        await self._set_attribute(Attribute.BRIGHTNESS, value)

    async def set_child_lock(self, value: str) -> None:
        """Set child lock state (C610+)."""
        _LOGGER.debug("client:set_child_lock(%s) device=%s", value, self._device_id)
        await self._set_attribute(Attribute.CHILD_LOCK, value)

    async def set_timer(self, value: str) -> None:
        """Set power-off timer (Tower XQ)."""
        _LOGGER.debug("client:set_timer(%s) device=%s", value, self._device_id)
        await self._set_attribute(Attribute.TIMER, value)

    async def _get_status_attributes(self) -> dict[str, str]:
        """Fetch raw status attributes from the device API."""
        url = URL_DEVICE_STATUS.format(device_id=self._device_id)

        async with self._session.get(url) as resp:
            if resp.status != 200:
                raise WinixApiError(f"Device status error: HTTP {resp.status}")
            data = await resp.json()

        result_message = data.get("headers", {}).get("resultMessage", "")
        body = data.get("body", {})
        body_data = body.get("data", [])

        if not body_data or _is_error(result_message):
            raise WinixApiError(
                f"Device status error: {result_message}",
                result_message=result_message,
            )

        return body_data[0].get("attributes", {})

    async def _set_attribute(self, attribute: str, value: str) -> None:
        """Send a control command to the device."""
        url = URL_DEVICE_CONTROL.format(
            device_id=self._device_id,
            attribute=attribute,
            value=value,
        )

        async with self._session.get(url) as resp:
            if resp.status != 200:
                raise WinixApiError(f"Device control error: HTTP {resp.status}")
            data = await resp.json()

        result_message = data.get("headers", {}).get("resultMessage", "")
        if _is_error(result_message):
            raise WinixApiError(
                f"Device control error: {result_message}",
                result_message=result_message,
            )

    @staticmethod
    def _parse_air_quality(attrs: dict[str, str]) -> AirQuality:
        """Parse air quality from raw attribute, handling both enum and float values."""
        raw = attrs.get(Attribute.AIR_QUALITY) or attrs.get(Attribute.AQI, "")

        # Direct enum match
        if raw in _AIR_QUALITY_VALUES:
            return AirQuality(raw)

        # Float-based mapping (some devices report a decimal value)
        try:
            quality = float(raw)
        except (ValueError, TypeError):
            return AirQuality.GOOD

        if quality >= 3.1:
            return AirQuality.VERY_POOR
        if quality >= 2.1:
            return AirQuality.POOR
        if quality >= 1.1:
            return AirQuality.FAIR
        return AirQuality.GOOD

    @staticmethod
    def _parse_int(value: str | None, default: int) -> int:
        if not value:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _parse_int_optional(value: str | None) -> int | None:
        if not value:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None


def _is_error(result_message: str) -> bool:
    """Check if an API response message indicates an error."""
    if not result_message:
        return False
    lower = result_message.lower()
    return any(err in lower for err in ("no data", "not valid", "not registered", "not connected"))
