"""Integration tests for Winix account management."""

from __future__ import annotations

import aiohttp
import pytest

from custom_components.winix_purifiers.api.account import WinixAccount

pytestmark = pytest.mark.skipif(
    "not config.getoption('--run-integration', default=False)",
    reason="Integration tests require --run-integration flag and env vars",
)


class TestAccount:
    """Test real account operations with encrypted mobile API."""

    async def test_from_credentials_and_get_devices(self, winix_username: str, winix_password: str):
        if not winix_username or not winix_password:
            pytest.skip("WINIX_USERNAME and WINIX_PASSWORD required")

        async with aiohttp.ClientSession() as session:
            account = await WinixAccount.from_credentials(session, winix_username, winix_password)

            devices = await account.get_devices()
            assert len(devices) > 0

            for device in devices:
                assert device.device_id
                assert device.model_name
