"""Unit tests for WinixAccount session establishment (v1.5.7 Cognito flow)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.winix_purifiers.api.account import WinixAccount
from custom_components.winix_purifiers.api.auth import WinixAuthResponse
from custom_components.winix_purifiers.api.exceptions import WinixApiError


def _make_auth(user_id: str = "user-sub-123") -> WinixAuthResponse:
    return WinixAuthResponse(
        user_id=user_id,
        access_token="access-token",
        id_token="id-token-abc",
        expires_at=9_999_999_999.0,
        refresh_token="refresh-token",
    )


def _make_account(auth: WinixAuthResponse | None = None) -> WinixAccount:
    return WinixAccount(
        session=MagicMock(),
        username="user@example.com",
        auth=auth or _make_auth(),
    )


class TestIdentityIdProperty:
    def test_raises_when_not_resolved(self):
        account = _make_account()
        with pytest.raises(WinixApiError):
            _ = account.identity_id

    def test_returns_resolved_value(self):
        account = _make_account()
        account._identity_id = "us-east-1:abc-123"
        assert account.identity_id == "us-east-1:abc-123"


class TestResolveIdentityId:
    async def test_calls_cognito_with_id_token(self):
        account = _make_account()

        fake_get_id = MagicMock(return_value={"IdentityId": "us-east-1:abc"})
        with patch(
            "custom_components.winix_purifiers.api.account.WinixAccount._get_identity_id_sync",
            fake_get_id,
        ):
            await account._resolve_identity_id()

        assert account.identity_id == "us-east-1:abc"
        fake_get_id.assert_called_once_with("id-token-abc")

    async def test_raises_when_cognito_returns_no_identity_id(self):
        account = _make_account()

        with (
            patch(
                "custom_components.winix_purifiers.api.account.WinixAccount._get_identity_id_sync",
                MagicMock(return_value={}),
            ),
            pytest.raises(WinixApiError),
        ):
            await account._resolve_identity_id()


class TestEstablishSessionOrder:
    """The v1.5.7 handshake order is load-bearing."""

    async def test_calls_steps_in_order(self):
        account = _make_account()
        calls: list[str] = []

        def make_step(name: str) -> AsyncMock:
            async def impl() -> None:
                calls.append(name)

            return AsyncMock(side_effect=impl)

        account._resolve_identity_id = make_step("resolve")
        account._register_user = make_step("register")
        account._init = make_step("init")
        account._check_access_token = make_step("check")

        await account._establish_session()

        assert calls == ["resolve", "register", "init", "check"]


class TestMobilePayloads:
    """Verify payloads contain identityId and no longer include cognitoClientSecretKey."""

    async def test_register_user_payload(self):
        account = _make_account()
        account._identity_id = "us-east-1:abc"
        account._mobile_post = AsyncMock(return_value={})

        await account._register_user()

        url, payload = account._mobile_post.call_args.args
        assert "registerUser" in url
        assert payload["identityId"] == "us-east-1:abc"
        assert payload["accessToken"] == "access-token"
        assert payload["email"] == "user@example.com"
        assert "cognitoClientSecretKey" not in payload

    async def test_init_payload(self):
        account = _make_account()
        account._mobile_post = AsyncMock(return_value={})

        await account._init()

        url, payload = account._mobile_post.call_args.args
        assert url.endswith("/init")
        assert payload == {
            "accessToken": "access-token",
            "uuid": account._uuid,
            "region": "US",
        }

    async def test_check_access_token_payload(self):
        account = _make_account()
        account._identity_id = "us-east-1:abc"
        account._mobile_post = AsyncMock(return_value={})

        await account._check_access_token()

        url, payload = account._mobile_post.call_args.args
        assert "checkAccessToken" in url
        assert payload["identityId"] == "us-east-1:abc"
        assert payload["accessToken"] == "access-token"
        assert "cognitoClientSecretKey" not in payload

    async def test_get_devices_payload(self):
        account = _make_account()
        account._identity_id = "us-east-1:abc"
        account._mobile_post = AsyncMock(return_value={"deviceInfoList": []})

        await account.get_devices()

        _, payload = account._mobile_post.call_args.args
        assert "cognitoClientSecretKey" not in payload
        assert payload["accessToken"] == "access-token"


class TestRefreshFlow:
    """v1.5.7: refresh must re-resolve identity_id and redo the mobile handshake."""

    async def test_refresh_reestablishes_session_and_updates_auth(self):
        account = _make_account(_make_auth("old-user"))

        new_auth = WinixAuthResponse(
            user_id="old-user",
            access_token="new-access",
            id_token="new-id",
            expires_at=9_999_999_999.0,
            refresh_token="old-refresh",
        )

        calls: list[str] = []

        async def fake_run_auth(fn, *args):
            calls.append("run_auth")
            return new_auth

        async def fake_establish():
            calls.append("establish")

        account._run_auth = fake_run_auth
        account._establish_session = fake_establish

        await account._refresh()

        assert calls == ["run_auth", "establish"]
        assert account.auth is new_auth
        assert account.auth.access_token == "new-access"

    async def test_get_access_token_triggers_refresh_when_expired(self):
        expired_auth = WinixAuthResponse(
            user_id="u",
            access_token="old-access",
            id_token="old-id",
            expires_at=0.0,
            refresh_token="r",
        )
        account = _make_account(expired_auth)

        refreshed = False

        async def fake_refresh():
            nonlocal refreshed
            refreshed = True
            account._auth = WinixAuthResponse(
                user_id="u",
                access_token="fresh-access",
                id_token="fresh-id",
                expires_at=9_999_999_999.0,
                refresh_token="r",
            )

        account._refresh = fake_refresh

        token = await account._get_access_token()

        assert refreshed is True
        assert token == "fresh-access"


class TestExecutorRouting:
    """Blocking auth calls must go through executor_fn when provided (HA event loop)."""

    async def test_run_auth_uses_executor_when_provided(self):
        captured: dict = {}

        async def fake_executor(fn, *args):
            captured["fn"] = fn
            captured["args"] = args
            return "executor-result"

        auth = _make_auth()
        account = WinixAccount(
            session=MagicMock(),
            username="u@example.com",
            auth=auth,
            executor_fn=fake_executor,
        )

        def blocking_fn(a, b):
            return f"{a}-{b}"

        result = await account._run_auth(blocking_fn, "x", "y")

        assert result == "executor-result"
        assert captured["fn"] is blocking_fn
        assert captured["args"] == ("x", "y")

    async def test_run_auth_calls_fn_directly_when_no_executor(self):
        account = _make_account()

        def blocking_fn(a, b):
            return f"{a}+{b}"

        result = await account._run_auth(blocking_fn, "hello", "world")

        assert result == "hello+world"


class TestUuidStability:
    """UUID should be derived from user_id deterministically."""

    def test_uuid_is_16_hex_chars(self):
        account = _make_account()
        assert len(account._uuid) == 16
        int(account._uuid, 16)  # parses as hex

    def test_same_user_id_same_uuid(self):
        a = _make_account(_make_auth("abc"))
        b = _make_account(_make_auth("abc"))
        assert a._uuid == b._uuid

    def test_different_user_id_different_uuid(self):
        a = _make_account(_make_auth("abc"))
        b = _make_account(_make_auth("xyz"))
        assert a._uuid != b._uuid
