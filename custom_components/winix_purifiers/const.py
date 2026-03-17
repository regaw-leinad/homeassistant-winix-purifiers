"""Constants for the Winix Purifiers integration."""

from __future__ import annotations

import logging

from .api import Airflow

DOMAIN = "winix_purifiers"
LOGGER = logging.getLogger(__package__)

DEFAULT_SCAN_INTERVAL = 30  # seconds

# Fan speed mapping (4 manual speeds, Sleep is a preset)
ORDERED_AIRFLOW_SPEEDS = [Airflow.LOW, Airflow.MEDIUM, Airflow.HIGH, Airflow.TURBO]

# Fan preset modes
PRESET_AUTO = "Auto"
PRESET_SLEEP = "Sleep"
PRESET_MODES = [PRESET_AUTO, PRESET_SLEEP]

# Reachability
UNREACHABLE_THRESHOLD = 3
MAX_BACKOFF_SECONDS = 300  # 5 minutes

# Command timing
COMMAND_DELAY_SECONDS = 1.5  # Delay between mode and airflow commands

# Filter
MAX_FILTER_HOURS = 6480
DEFAULT_FILTER_REPLACEMENT_THRESHOLD = 10  # percent
