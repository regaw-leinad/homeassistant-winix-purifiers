"""Tests for device enums, types, and model capabilities."""

from custom_components.winix_purifiers.api.device import (
    Airflow,
    AirQuality,
    Attribute,
    DeviceStatus,
    Mode,
    ModelCapabilities,
    Plasmawave,
    Power,
)


class TestEnums:
    """Test device enum values match the Winix API protocol."""

    def test_power_values(self):
        assert Power.OFF == "0"
        assert Power.ON == "1"

    def test_mode_values(self):
        assert Mode.AUTO == "01"
        assert Mode.MANUAL == "02"

    def test_airflow_values(self):
        assert Airflow.LOW == "01"
        assert Airflow.MEDIUM == "02"
        assert Airflow.HIGH == "03"
        assert Airflow.TURBO == "05"
        assert Airflow.SLEEP == "06"

    def test_air_quality_values(self):
        assert AirQuality.GOOD == "01"
        assert AirQuality.FAIR == "02"
        assert AirQuality.POOR == "03"
        assert AirQuality.VERY_POOR == "04"

    def test_plasmawave_values(self):
        assert Plasmawave.OFF == "0"
        assert Plasmawave.ON == "1"

    def test_attribute_codes(self):
        assert Attribute.POWER == "A02"
        assert Attribute.MODE == "A03"
        assert Attribute.AIRFLOW == "A04"
        assert Attribute.PLASMAWAVE == "A07"
        assert Attribute.FILTER_HOURS == "A21"
        assert Attribute.AIR_QUALITY == "S07"
        assert Attribute.AMBIENT_LIGHT == "S14"
        assert Attribute.PM25 == "S04"
        assert Attribute.TIMER == "A15"


class TestDeviceStatus:
    """Test DeviceStatus dataclass."""

    def test_required_fields(self):
        status = DeviceStatus(
            power=Power.ON,
            mode=Mode.AUTO,
            airflow=Airflow.LOW,
            air_quality=AirQuality.GOOD,
            plasmawave=Plasmawave.ON,
            filter_hours=100,
        )
        assert status.power == Power.ON
        assert status.ambient_light is None
        assert status.pm25 is None
        assert status.timer is None

    def test_optional_fields(self):
        status = DeviceStatus(
            power=Power.ON,
            mode=Mode.MANUAL,
            airflow=Airflow.HIGH,
            air_quality=AirQuality.POOR,
            plasmawave=Plasmawave.OFF,
            filter_hours=5000,
            ambient_light=42,
            pm25=15,
            timer=4,
        )
        assert status.ambient_light == 42
        assert status.pm25 == 15
        assert status.timer == 4


class TestModelCapabilities:
    """Test per-model capability detection."""

    def test_c545_basic(self):
        caps = ModelCapabilities(
            model_name="C545",
            available_attributes={
                Attribute.POWER,
                Attribute.MODE,
                Attribute.AIRFLOW,
                Attribute.PLASMAWAVE,
                Attribute.FILTER_HOURS,
                Attribute.AIR_QUALITY,
                Attribute.AMBIENT_LIGHT,
            },
        )
        assert not caps.has_brightness
        assert not caps.has_child_lock  # no A08 in attributes
        assert caps.has_ambient_light
        assert not caps.has_pm25
        assert not caps.has_timer
        assert not caps.has_four_level_aqi

    def test_c610_extended(self):
        caps = ModelCapabilities(
            model_name="C610",
            available_attributes={
                Attribute.POWER,
                Attribute.MODE,
                Attribute.AIRFLOW,
                Attribute.PLASMAWAVE,
                Attribute.CHILD_LOCK,
            },
        )
        assert caps.has_brightness
        assert caps.has_child_lock
        assert not caps.has_pm25

    def test_tower_xq(self):
        caps = ModelCapabilities(
            model_name="TOWERXQ_WA",
            available_attributes={
                Attribute.POWER,
                Attribute.MODE,
                Attribute.AIRFLOW,
                Attribute.PLASMAWAVE,
                Attribute.PM25,
                Attribute.TIMER,
                Attribute.CHILD_LOCK,
            },
        )
        assert caps.has_pm25
        assert caps.has_timer
        assert caps.has_child_lock
        assert caps.has_four_level_aqi
        assert not caps.has_ambient_light
        assert not caps.has_brightness

    def test_unknown_model_detects_from_attributes(self):
        """Unknown models should detect capabilities from available attributes."""
        caps = ModelCapabilities(
            model_name="UNKNOWN_MODEL",
            available_attributes={Attribute.PM25, Attribute.AMBIENT_LIGHT},
        )
        assert caps.has_pm25
        assert caps.has_ambient_light
        assert not caps.has_brightness
        assert not caps.has_timer
