"""Tests for fan speed mapping and preset logic."""

from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from custom_components.winix_purifiers.api.device import Airflow
from custom_components.winix_purifiers.const import (
    ORDERED_AIRFLOW_SPEEDS,
    PRESET_AUTO,
    PRESET_SLEEP,
)


class TestSpeedMapping:
    """Test airflow-to-percentage mapping."""

    def test_low_is_25(self):
        assert ordered_list_item_to_percentage(ORDERED_AIRFLOW_SPEEDS, Airflow.LOW) == 25

    def test_medium_is_50(self):
        assert ordered_list_item_to_percentage(ORDERED_AIRFLOW_SPEEDS, Airflow.MEDIUM) == 50

    def test_high_is_75(self):
        assert ordered_list_item_to_percentage(ORDERED_AIRFLOW_SPEEDS, Airflow.HIGH) == 75

    def test_turbo_is_100(self):
        assert ordered_list_item_to_percentage(ORDERED_AIRFLOW_SPEEDS, Airflow.TURBO) == 100

    def test_speed_count(self):
        assert len(ORDERED_AIRFLOW_SPEEDS) == 4


class TestPercentageToAirflow:
    """Test percentage-to-airflow mapping."""

    def test_25_is_low(self):
        assert percentage_to_ordered_list_item(ORDERED_AIRFLOW_SPEEDS, 25) == Airflow.LOW

    def test_50_is_medium(self):
        assert percentage_to_ordered_list_item(ORDERED_AIRFLOW_SPEEDS, 50) == Airflow.MEDIUM

    def test_75_is_high(self):
        assert percentage_to_ordered_list_item(ORDERED_AIRFLOW_SPEEDS, 75) == Airflow.HIGH

    def test_100_is_turbo(self):
        assert percentage_to_ordered_list_item(ORDERED_AIRFLOW_SPEEDS, 100) == Airflow.TURBO

    def test_1_maps_to_low(self):
        """Minimum non-zero percentage should map to lowest speed."""
        assert percentage_to_ordered_list_item(ORDERED_AIRFLOW_SPEEDS, 1) == Airflow.LOW

    def test_99_maps_to_turbo(self):
        """Near-max percentage should map to highest speed."""
        assert percentage_to_ordered_list_item(ORDERED_AIRFLOW_SPEEDS, 99) == Airflow.TURBO


class TestPresetModes:
    """Test preset mode constants."""

    def test_preset_auto(self):
        assert PRESET_AUTO == "Auto"

    def test_preset_sleep(self):
        assert PRESET_SLEEP == "Sleep"

    def test_sleep_not_in_speed_list(self):
        """Sleep airflow should not be in the ordered speed list."""
        assert Airflow.SLEEP not in ORDERED_AIRFLOW_SPEEDS
