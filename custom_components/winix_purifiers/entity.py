"""Base entity for Winix Purifiers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, UNREACHABLE_THRESHOLD

if TYPE_CHECKING:
    from .coordinator import WinixDeviceCoordinator, WinixDeviceData


class WinixEntity(CoordinatorEntity["WinixDeviceCoordinator"]):
    """Base class for all Winix entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WinixDeviceCoordinator) -> None:
        super().__init__(coordinator)

        info = self.device_data.info

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, info.mac.lower())},
            name=info.device_alias,
            manufacturer="Winix",
            model=info.model_name,
            sw_version=info.mcu_ver,
        )

    @property
    def device_data(self) -> WinixDeviceData:
        return self.coordinator.data

    @property
    def available(self) -> bool:
        data = self.device_data
        return data.has_received_data and data.consecutive_failures < UNREACHABLE_THRESHOLD
