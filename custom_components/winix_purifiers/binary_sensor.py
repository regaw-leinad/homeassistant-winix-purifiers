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

from .const import (
    CONF_FILTER_REPLACEMENT_THRESHOLD,
    DEFAULT_FILTER_REPLACEMENT_THRESHOLD,
    DOMAIN,
    MAX_FILTER_HOURS,
)
from .coordinator import WinixDeviceCoordinator
from .entity import WinixEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Winix binary sensor entities."""
    coordinators: dict[str, WinixDeviceCoordinator] = hass.data[DOMAIN][entry.entry_id]
    threshold = entry.options.get(
        CONF_FILTER_REPLACEMENT_THRESHOLD, DEFAULT_FILTER_REPLACEMENT_THRESHOLD
    )
    entities: list[BinarySensorEntity] = []

    for coordinator in coordinators.values():
        caps = coordinator.data.capabilities

        entities.append(WinixFilterReplacementSensor(coordinator, threshold))

        if caps.has_filter_door:
            entities.append(WinixFilterDoorSensor(coordinator))
        if caps.has_filter_detect:
            entities.append(WinixFilterDetectSensor(coordinator))

    async_add_entities(entities)


class WinixFilterReplacementSensor(WinixEntity, BinarySensorEntity):
    """Filter replacement alert, on when filter life is below threshold."""

    _attr_translation_key = "filter_replacement"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: WinixDeviceCoordinator,
        threshold: int,
    ) -> None:
        super().__init__(coordinator)
        self._threshold = threshold
        mac = self.device_data.info.mac.lower()
        self._attr_unique_id = f"{DOMAIN}_{mac}_filter_replacement"

    @property
    def is_on(self) -> bool:
        hours = self.device_data.status.filter_hours
        if hours <= 0:
            return False
        remaining = max(MAX_FILTER_HOURS - hours, 0)
        percentage = round((remaining / MAX_FILTER_HOURS) * 100)
        return percentage <= self._threshold


class WinixFilterDoorSensor(WinixEntity, BinarySensorEntity):
    """Filter door open/closed sensor (XLC)."""

    _attr_translation_key = "filter_door"
    _attr_device_class = BinarySensorDeviceClass.DOOR
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: WinixDeviceCoordinator) -> None:
        super().__init__(coordinator)
        mac = self.device_data.info.mac.lower()
        self._attr_unique_id = f"{DOMAIN}_{mac}_filter_door"

    @property
    def is_on(self) -> bool:
        return self.device_data.status.filter_door == "1"


class WinixFilterDetectSensor(WinixEntity, BinarySensorEntity):
    """Filter presence detection sensor (XLC). On when filter is missing."""

    _attr_translation_key = "filter_detect"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: WinixDeviceCoordinator) -> None:
        super().__init__(coordinator)
        mac = self.device_data.info.mac.lower()
        self._attr_unique_id = f"{DOMAIN}_{mac}_filter_detect"

    @property
    def is_on(self) -> bool:
        # "0" = not detected = problem, "1" = detected = ok
        return self.device_data.status.filter_detect == "0"
