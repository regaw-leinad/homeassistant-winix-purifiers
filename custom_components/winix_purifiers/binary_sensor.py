"""Binary sensor entities for Winix purifiers."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEFAULT_FILTER_REPLACEMENT_THRESHOLD, DOMAIN, MAX_FILTER_HOURS
from .coordinator import WinixDeviceCoordinator
from .entity import WinixEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Winix binary sensor entities."""
    coordinators: dict[str, WinixDeviceCoordinator] = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        WinixFilterReplacementSensor(coordinator) for coordinator in coordinators.values()
    )


class WinixFilterReplacementSensor(WinixEntity, BinarySensorEntity):
    """Filter replacement alert, on when filter life is below threshold."""

    _attr_translation_key = "filter_replacement"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: WinixDeviceCoordinator,
    ) -> None:
        super().__init__(coordinator)
        mac = self.device_data.info.mac.lower()
        self._attr_unique_id = f"{DOMAIN}_{mac}_filter_replacement"

    @property
    def is_on(self) -> bool:
        hours = self.device_data.status.filter_hours
        if hours <= 0:
            return False
        remaining = max(MAX_FILTER_HOURS - hours, 0)
        percentage = round((remaining / MAX_FILTER_HOURS) * 100)
        return percentage <= DEFAULT_FILTER_REPLACEMENT_THRESHOLD
