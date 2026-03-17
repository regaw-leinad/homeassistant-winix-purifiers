"""Integration tests for device control, hits real Winix API."""

from __future__ import annotations

import asyncio

import aiohttp
import pytest

from custom_components.winix_purifiers.api.client import WinixDeviceClient
from custom_components.winix_purifiers.api.device import Airflow, Mode, Power

# Device needs time to process commands before status API reflects changes
SETTLE_SECONDS = 8

pytestmark = pytest.mark.skipif(
    "not config.getoption('--run-integration', default=False)",
    reason="Integration tests require --run-integration flag and env vars",
)


async def settle():
    await asyncio.sleep(SETTLE_SECONDS)


class TestDeviceControl:
    """Test real device control operations."""

    async def test_get_status(self, winix_device_id: str):
        if not winix_device_id:
            pytest.skip("WINIX_DEVICE_ID required")

        async with aiohttp.ClientSession() as session:
            client = WinixDeviceClient(session, winix_device_id)
            status = await client.get_status()

            assert status.power in (Power.ON, Power.OFF)
            assert status.mode in (Mode.AUTO, Mode.MANUAL)
            assert status.airflow in tuple(Airflow)

    async def test_power_cycle(self, winix_device_id: str):
        if not winix_device_id:
            pytest.skip("WINIX_DEVICE_ID required")

        async with aiohttp.ClientSession() as session:
            client = WinixDeviceClient(session, winix_device_id)

            # Save original state
            original = await client.get_status()

            # Turn off
            await client.set_power(Power.OFF)
            await settle()
            status = await client.get_status()
            assert status.power == Power.OFF

            # Turn on
            await client.set_power(Power.ON)
            await settle()
            status = await client.get_status()
            assert status.power == Power.ON

            # Restore original power state
            await client.set_power(original.power)
            await settle()

    async def test_mode_and_airflow(self, winix_device_id: str):
        if not winix_device_id:
            pytest.skip("WINIX_DEVICE_ID required")

        async with aiohttp.ClientSession() as session:
            client = WinixDeviceClient(session, winix_device_id)

            # Save original state
            original = await client.get_status()

            # Set manual mode
            await client.set_mode(Mode.MANUAL)
            await settle()

            # Set high airflow
            await client.set_airflow(Airflow.HIGH)
            await settle()

            status = await client.get_status()
            assert status.mode == Mode.MANUAL
            assert status.airflow == Airflow.HIGH

            # Restore original state
            await client.set_mode(original.mode)
            await settle()
            await client.set_airflow(original.airflow)
            await settle()
            await client.set_power(original.power)
            await settle()
