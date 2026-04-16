"""Unit tests for WinixDeviceClient URL building and identity id wiring."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.winix_purifiers.api.client import WinixDeviceClient
from custom_components.winix_purifiers.api.device import Power


def _make_session(response_json: dict | None = None) -> MagicMock:
    """Build a mock aiohttp session that returns the given JSON from GET."""
    resp = MagicMock()
    resp.status = 200
    resp.json = AsyncMock(return_value=response_json or {"headers": {"resultMessage": ""}})

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=None)

    session = MagicMock()
    session.get = MagicMock(return_value=ctx)
    return session


class TestConstructor:
    def test_requires_non_empty_identity_id(self):
        with pytest.raises(ValueError):
            WinixDeviceClient(MagicMock(), "dev123", "")

    def test_accepts_identity_id(self):
        client = WinixDeviceClient(MagicMock(), "dev123", "us-east-1:abc")
        assert client.device_id == "dev123"


class TestControlUrl:
    """Verify set_* operations build the v1.5.7 control URL with identityId."""

    async def test_set_power_url_contains_identity_id(self):
        session = _make_session()
        client = WinixDeviceClient(session, "dev123", "us-east-1:abc-123")

        await client.set_power(Power.ON)

        assert session.get.call_count == 1
        url = session.get.call_args.args[0]
        assert url == (
            "https://us.api.winix-iot.com/common/control/devices/dev123" "/us-east-1:abc-123/A02:1"
        )

    async def test_set_power_off_uses_correct_value(self):
        session = _make_session()
        client = WinixDeviceClient(session, "dev999", "us-east-1:xyz")

        await client.set_power(Power.OFF)

        url = session.get.call_args.args[0]
        assert url.endswith("/us-east-1:xyz/A02:0")

    async def test_no_a211_segment_in_url(self):
        """Regression guard: old hardcoded /A211/ segment must not appear."""
        session = _make_session()
        client = WinixDeviceClient(session, "dev123", "us-east-1:abc")

        await client.set_power(Power.ON)

        url = session.get.call_args.args[0]
        assert "/A211/" not in url

    async def test_set_mode_also_uses_identity_id(self):
        """All setters (not just power) must embed identityId."""
        from custom_components.winix_purifiers.api.device import Mode

        session = _make_session()
        client = WinixDeviceClient(session, "dev42", "us-east-1:xyz")

        await client.set_mode(Mode.MANUAL)

        url = session.get.call_args.args[0]
        assert url == (
            "https://us.api.winix-iot.com/common/control/devices/dev42" "/us-east-1:xyz/A03:02"
        )


class TestStatusUrl:
    """Status URL must remain unchanged (no identity_id) - only control URL got the new segment."""

    async def test_status_url_does_not_contain_identity_id(self):
        session = _make_session(
            response_json={
                "headers": {"resultMessage": ""},
                "body": {
                    "data": [{"attributes": {"A02": "1", "A03": "01", "A04": "01", "A21": "0"}}]
                },
            }
        )
        client = WinixDeviceClient(session, "dev123", "us-east-1:should-not-appear")

        await client.get_status()

        url = session.get.call_args.args[0]
        assert url == "https://us.api.winix-iot.com/common/event/sttus/devices/dev123"
        assert "us-east-1:should-not-appear" not in url
