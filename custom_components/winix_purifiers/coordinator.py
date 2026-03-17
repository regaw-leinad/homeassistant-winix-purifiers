"""Per-device data coordinator for Winix Purifiers."""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import (
    DeviceStatus,
    ModelCapabilities,
    WinixDevice,
    WinixDeviceClient,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, UNREACHABLE_THRESHOLD

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


class WinixDeviceCoordinator(DataUpdateCoordinator[WinixDeviceData]):
    """Coordinator that polls a single Winix device independently."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        device_data: WinixDeviceData,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        name = device_data.info.device_alias
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{name}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self._device_data = device_data

    @property
    def device_id(self) -> str:
        return self._device_data.info.device_id

    async def _async_update_data(self) -> WinixDeviceData:
        """Poll this device for current status."""
        data = self._device_data
        name = data.info.device_alias

        try:
            data.status = await data.client.get_status()
            data.has_received_data = True
            data.consecutive_failures = 0
            _LOGGER.debug("coordinator:poll(%s) success", name)
        except Exception as err:
            data.consecutive_failures += 1
            if data.consecutive_failures == 1:
                _LOGGER.debug("coordinator:poll(%s) device unavailable: %s", name, err)
            elif data.consecutive_failures == UNREACHABLE_THRESHOLD:
                _LOGGER.debug(
                    "coordinator:poll(%s) marking as unreachable after %d failures",
                    name,
                    data.consecutive_failures,
                )

        return data

    async def async_send_command(
        self,
        command: Callable[[], Coroutine[Any, Any, None]],
        optimistic_update: Callable[[DeviceStatus], None] | None = None,
    ) -> None:
        """Send a command to this device with optimistic state update."""
        if optimistic_update:
            optimistic_update(self._device_data.status)
            self.async_set_updated_data(self._device_data)

        await command()
