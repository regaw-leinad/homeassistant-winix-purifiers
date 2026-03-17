"""Integration tests for Winix authentication."""

from __future__ import annotations

import pytest

from custom_components.winix_purifiers.api.auth import WinixAuth, WinixAuthResponse

pytestmark = pytest.mark.skipif(
    "not config.getoption('--run-integration', default=False)",
    reason="Integration tests require --run-integration flag and env vars",
)


class TestLogin:
    """Test real Cognito login."""

    def test_login_returns_valid_response(self, winix_username: str, winix_password: str):
        if not winix_username or not winix_password:
            pytest.skip("WINIX_USERNAME and WINIX_PASSWORD required")

        auth = WinixAuth.login(winix_username, winix_password)

        assert isinstance(auth, WinixAuthResponse)
        assert auth.user_id
        assert auth.access_token
        assert auth.refresh_token
        assert auth.expires_at > 0

    def test_refresh_returns_valid_response(self, winix_username: str, winix_password: str):
        if not winix_username or not winix_password:
            pytest.skip("WINIX_USERNAME and WINIX_PASSWORD required")

        auth = WinixAuth.login(winix_username, winix_password)
        refreshed = WinixAuth.refresh(auth.refresh_token, auth.user_id)

        assert isinstance(refreshed, WinixAuthResponse)
        assert refreshed.access_token
        assert refreshed.user_id == auth.user_id
