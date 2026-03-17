"""Sensor entities for Winix purifiers."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import LIGHT_LUX, PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import AirQuality
from .const import DOMAIN, MAX_FILTER_HOURS
from .coordinator import WinixDeviceCoordinator
from .entity import WinixEntity

# Map Winix AQI enum to approximate EPA AQI values
_AQI_MAP = {
    AirQuality.GOOD: 25,
    AirQuality.FAIR: 75,
    AirQuality.POOR: 150,
    AirQuality.VERY_POOR: 200,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Winix sensor entities."""
    coordinators: dict[str, WinixDeviceCoordinator] = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    for coordinator in coordinators.values():
        caps = coordinator.data.capabilities

        # Always available
        entities.append(WinixAirQualitySensor(coordinator))
        entities.append(WinixFilterLifeSensor(coordinator))

        # Model-dependent
        if caps.has_ambient_light:
            entities.append(WinixAmbientLightSensor(coordinator))
        if caps.has_pm25:
            entities.append(WinixPM25Sensor(coordinator))

    async_add_entities(entities)


class WinixAirQualitySensor(WinixEntity, SensorEntity):
    """Air quality index sensor."""

    _attr_translation_key = "air_quality"
    _attr_device_class = SensorDeviceClass.AQI
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: WinixDeviceCoordinator) -> None:
        super().__init__(coordinator)
        mac = self.device_data.info.mac.lower()
        self._attr_unique_id = f"{DOMAIN}_{mac}_air_quality"

    @property
    def native_value(self) -> int | None:
        return _AQI_MAP.get(self.device_data.status.air_quality)


class WinixPM25Sensor(WinixEntity, SensorEntity):
    """PM2.5 particulate sensor (Tower XQ, T800)."""

    _attr_translation_key = "pm25"
    _attr_device_class = SensorDeviceClass.PM25
    _attr_native_unit_of_measurement = "µg/m³"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: WinixDeviceCoordinator) -> None:
        super().__init__(coordinator)
        mac = self.device_data.info.mac.lower()
        self._attr_unique_id = f"{DOMAIN}_{mac}_pm25"

    @property
    def native_value(self) -> int | None:
        return self.device_data.status.pm25


class WinixAmbientLightSensor(WinixEntity, SensorEntity):
    """Ambient light sensor."""

    _attr_translation_key = "ambient_light"
    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_native_unit_of_measurement = LIGHT_LUX
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: WinixDeviceCoordinator) -> None:
        super().__init__(coordinator)
        mac = self.device_data.info.mac.lower()
        self._attr_unique_id = f"{DOMAIN}_{mac}_ambient_light"

    @property
    def native_value(self) -> int | None:
        return self.device_data.status.ambient_light


class WinixFilterLifeSensor(WinixEntity, SensorEntity):
    """Filter life remaining percentage."""

    _attr_translation_key = "filter_life"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: WinixDeviceCoordinator) -> None:
        super().__init__(coordinator)
        mac = self.device_data.info.mac.lower()
        self._attr_unique_id = f"{DOMAIN}_{mac}_filter_life"

    @property
    def native_value(self) -> int:
        hours = self.device_data.status.filter_hours
        if hours <= 0:
            return 100
        remaining = max(MAX_FILTER_HOURS - hours, 0)
        return round((remaining / MAX_FILTER_HOURS) * 100)
