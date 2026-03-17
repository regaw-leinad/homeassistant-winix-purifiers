"""Winix device models, enums, and types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Attribute(StrEnum):
    """Device status/control attribute codes."""

    POWER = "A02"
    MODE = "A03"
    AIRFLOW = "A04"
    AQI = "A05"
    PLASMAWAVE = "A07"
    CHILD_LOCK = "A08"
    TIMER = "A15"
    BRIGHTNESS = "A16"
    FILTER_HOURS = "A21"
    PM25 = "S04"
    AIR_QUALITY = "S07"
    AIR_QVALUE = "S08"
    AMBIENT_LIGHT = "S14"


class Power(StrEnum):
    OFF = "0"
    ON = "1"


class Mode(StrEnum):
    AUTO = "01"
    MANUAL = "02"


class Airflow(StrEnum):
    LOW = "01"
    MEDIUM = "02"
    HIGH = "03"
    TURBO = "05"
    SLEEP = "06"


class AirQuality(StrEnum):
    GOOD = "01"
    FAIR = "02"
    POOR = "03"
    VERY_POOR = "04"  # Tower XQ has 4 levels


class Plasmawave(StrEnum):
    OFF = "0"
    ON = "1"


@dataclass
class DeviceStatus:
    """Parsed device status from the IoT API."""

    power: Power
    mode: Mode
    airflow: Airflow
    air_quality: AirQuality
    plasmawave: Plasmawave
    filter_hours: int
    air_qvalue: int | None = None
    # Model-dependent fields
    ambient_light: int | None = None
    pm25: int | None = None
    timer: int | None = None
    child_lock: str | None = None
    brightness: str | None = None


@dataclass
class WinixDevice:
    """Device metadata from getDeviceInfoList API."""

    device_id: str
    mac: str
    device_alias: str
    model_name: str
    mcu_ver: str = ""
    wifi_ver: str = ""
    device_loc_code: str = ""
    filter_replace_date: str = ""
    filter_alarm_month: str | None = None
    # Raw attributes from first status poll, used for capability detection
    raw_attributes: dict[str, str] = field(default_factory=dict)


@dataclass
class ModelCapabilities:
    """Feature detection based on model name and available attributes."""

    model_name: str
    available_attributes: set[str] = field(default_factory=set)

    @property
    def _model_lower(self) -> str:
        return self.model_name.lower()

    @property
    def has_brightness(self) -> bool:
        return self._model_lower.startswith("c610")

    @property
    def has_child_lock(self) -> bool:
        return (
            self._model_lower.startswith("c610")
            or Attribute.CHILD_LOCK in self.available_attributes
        )

    @property
    def has_ambient_light(self) -> bool:
        return Attribute.AMBIENT_LIGHT in self.available_attributes

    @property
    def has_pm25(self) -> bool:
        return Attribute.PM25 in self.available_attributes

    @property
    def has_timer(self) -> bool:
        return Attribute.TIMER in self.available_attributes

    @property
    def has_four_level_aqi(self) -> bool:
        """Tower XQ and similar models have 4 AQI levels instead of 3."""
        return "towerxq" in self._model_lower
