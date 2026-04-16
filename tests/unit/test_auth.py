"""Unit tests for WinixAuthResponse and refresh flow (no Cognito contacted)."""

from __future__ import annotations

from dataclasses import fields
from unittest.mock import MagicMock, patch

import pytest

from custom_components.winix_purifiers.api.auth import WinixAuth, WinixAuthResponse
from custom_components.winix_purifiers.api.exceptions import RefreshTokenExpiredError


class TestWinixAuthResponse:
    def test_has_id_token_field(self):
        """id_token was added in v1.5.7 for Cognito identity pool login."""
        field_names = {f.name for f in fields(WinixAuthResponse)}
        assert "id_token" in field_names

    def test_all_required_fields(self):
        field_names = {f.name for f in fields(WinixAuthResponse)}
        assert field_names == {
            "user_id",
            "access_token",
            "id_token",
            "expires_at",
            "refresh_token",
        }


class TestRefresh:
    """WinixAuth.refresh no longer sends SECRET_HASH (public client as of v1.5.7)."""

    def test_refresh_does_not_send_secret_hash(self):
        mock_client = MagicMock()
        mock_client.initiate_auth.return_value = {
            "AuthenticationResult": {
                "AccessToken": "new-access",
                "IdToken": "new-id",
                "ExpiresIn": 3600,
            }
        }
        mock_client.exceptions.NotAuthorizedException = Exception

        with patch(
            "custom_components.winix_purifiers.api.auth.boto3.client",
            return_value=mock_client,
        ):
            result = WinixAuth.refresh("refresh-token", "user-id")

        call = mock_client.initiate_auth.call_args
        auth_params = call.kwargs["AuthParameters"]
        assert auth_params == {"REFRESH_TOKEN": "refresh-token"}
        assert "SECRET_HASH" not in auth_params

        assert result.access_token == "new-access"
        assert result.id_token == "new-id"
        assert result.user_id == "user-id"
        assert result.refresh_token == "refresh-token"

    def test_do_login_constructs_warrant_lite_with_no_client_secret(self):
        """Regression guard: Winix moved to a public (secretless) Cognito client in v1.5.7."""
        captured: dict = {}

        class FakeWarrantLite:
            def __init__(self, *, username, password, pool_id, client_id, client_secret, client):
                captured["client_secret"] = client_secret
                captured["client_id"] = client_id

            def authenticate_user(self):
                return {
                    "AuthenticationResult": {
                        "AccessToken": (
                            # Token with sub=test-sub in claims, unsigned payload is enough
                            # since jose.jwt.get_unverified_claims does not verify
                            "eyJhbGciOiJub25lIn0." "eyJzdWIiOiJ0ZXN0LXN1YiJ9."
                        ),
                        "IdToken": "id-tok",
                        "RefreshToken": "ref-tok",
                        "ExpiresIn": 3600,
                    }
                }

        with patch(
            "custom_components.winix_purifiers.api.auth.WarrantLite",
            FakeWarrantLite,
        ):
            result = WinixAuth._do_login("u@example.com", "pw")

        assert captured["client_secret"] is None
        assert captured["client_id"] == "5rjk59c5tt7k9g8gpj0vd2qfg9"
        assert result.user_id == "test-sub"
        assert result.id_token == "id-tok"
        assert result.refresh_token == "ref-tok"

    def test_refresh_translates_not_authorized_to_expired_error(self):
        class FakeNotAuthorized(Exception):
            pass

        mock_client = MagicMock()
        mock_client.exceptions.NotAuthorizedException = FakeNotAuthorized
        mock_client.initiate_auth.side_effect = FakeNotAuthorized("nope")

        with (
            patch(
                "custom_components.winix_purifiers.api.auth.boto3.client",
                return_value=mock_client,
            ),
            pytest.raises(RefreshTokenExpiredError),
        ):
            WinixAuth.refresh("refresh-token", "user-id")
