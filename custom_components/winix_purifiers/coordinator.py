"""Data coordinator for Winix Purifiers."""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import (
    DeviceStatus,
    ModelCapabilities,
    WinixAccount,
    WinixDevice,
    WinixDeviceClient,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, MAX_BACKOFF_SECONDS, UNREACHABLE_THRESHOLD

_LOGGER = logging.getLogger(__name__)


@dataclass
class WinixDeviceData:
    """Runtime state for a single Winix device."""

    info: WinixDevice
    status: DeviceStatus
    capabilities: ModelCapabilities
    client: WinixDeviceClient
    consecutive_failures: int = 0
    has_received_data: bool = False
    _backoff_seconds: float = field(default=0, repr=False)


class WinixPurifiersCoordinator(DataUpdateCoordinator[dict[str, WinixDeviceData]]):
    """Coordinator that polls all Winix devices on an account."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        account: WinixAccount,
        devices: list[WinixDevice],
        clients: dict[str, WinixDeviceClient],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self._account = account
        self._device_data: dict[str, WinixDeviceData] = {}

        for device in devices:
            caps = ModelCapabilities(
                model_name=device.model_name,
                available_attributes=set(device.raw_attributes.keys()),
            )
            # Build initial status from raw_attributes if available
            client = clients[device.device_id]
            self._device_data[device.device_id] = WinixDeviceData(
                info=device,
                status=DeviceStatus(
                    power="0",
                    mode="01",
                    airflow="01",
                    air_quality="01",
                    plasmawave="0",
                    filter_hours=0,
                ),
                capabilities=caps,
                client=client,
            )

    @property
    def account(self) -> WinixAccount:
        return self._account

    def get_device_ids(self) -> list[str]:
        return list(self._device_data.keys())

    def get_device_data(self, device_id: str) -> WinixDeviceData:
        return self._device_data[device_id]

    async def _async_update_data(self) -> dict[str, WinixDeviceData]:
        """Poll all devices for current status."""
        for device_id, device_data in self._device_data.items():
            await self._poll_device(device_id, device_data)

        return self._device_data

    async def _poll_device(self, device_id: str, device_data: WinixDeviceData) -> None:
        """Poll a single device, with per-device failure tracking."""
        name = device_data.info.device_alias

        try:
            status = await device_data.client.get_status()
            device_data.status = status
            device_data.has_received_data = True
            device_data.consecutive_failures = 0
            device_data._backoff_seconds = 0
            _LOGGER.debug("coordinator:poll(%s) success", name)
        except Exception as err:
            device_data.consecutive_failures += 1
            device_data._backoff_seconds = min(
                DEFAULT_SCAN_INTERVAL * math.pow(2, device_data.consecutive_failures),
                MAX_BACKOFF_SECONDS,
            )
            # Only log on first failure and when marking unreachable
            if device_data.consecutive_failures == 1:
                _LOGGER.debug("coordinator:poll(%s) device unavailable: %s", name, err)
            elif device_data.consecutive_failures == UNREACHABLE_THRESHOLD:
                _LOGGER.debug(
                    "coordinator:poll(%s) marking as unreachable after %d failures",
                    name,
                    device_data.consecutive_failures,
                )

    async def async_send_command(
        self,
        device_id: str,
        command: Callable[[], Coroutine[Any, Any, None]],
        optimistic_update: Callable[[DeviceStatus], None] | None = None,
    ) -> None:
        """Send a command to a device with optimistic state update."""
        # Apply optimistic update before the API call
        if optimistic_update:
            device_data = self._device_data[device_id]
            optimistic_update(device_data.status)
            self.async_set_updated_data(self._device_data)

        await command()
