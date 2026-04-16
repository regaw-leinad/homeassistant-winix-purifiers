"""Winix account management, device listing and token lifecycle."""

from __future__ import annotations

import binascii
import logging
import time
from typing import Any

import aiohttp
import boto3
from botocore import UNSIGNED
from botocore.config import Config as BotoConfig

from .auth import WinixAuth, WinixAuthResponse
from .const import (
    COGNITO_IDENTITY_POOL_ID,
    COGNITO_REGION,
    COGNITO_USER_POOL_ID,
    MOBILE_APP_VERSION,
    MOBILE_LANG,
    MOBILE_MODEL,
    MOBILE_OS_TYPE,
    MOBILE_OS_VERSION,
    TOKEN_EXPIRY_BUFFER_SECONDS,
    URL_CHECK_ACCESS_TOKEN,
    URL_GET_DEVICE_INFO_LIST,
    URL_INIT,
    URL_REGISTER_USER,
    UUID_PREFIX,
    UUID_SUFFIX,
)
from .crypto import decrypt, encrypt
from .device import WinixDevice
from .exceptions import WinixApiError

_COGNITO_LOGINS_PROVIDER = f"cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"

_LOGGER = logging.getLogger(__name__)


class WinixAccount:
    """Manages a Winix account session with encrypted mobile API calls."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        auth: WinixAuthResponse,
        *,
        executor_fn: Any = None,
    ) -> None:
        self._session = session
        self._username = username
        self._auth = auth
        self._uuid = self._generate_uuid(auth.user_id)
        self._identity_id: str | None = None
        # Used to run boto3 (sync) calls off the event loop when in HA.
        self._executor_fn = executor_fn

    @classmethod
    async def from_credentials(
        cls,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        *,
        login_fn: Any = None,
    ) -> WinixAccount:
        """Create an account by logging in with username/password.

        login_fn can be provided to run the blocking auth in an executor
        (e.g., hass.async_add_executor_job). If None, calls synchronously.
        """
        if login_fn:
            auth = await login_fn(WinixAuth.login, username, password)
        else:
            auth = WinixAuth.login(username, password)

        return await cls._create(session, username, auth, executor_fn=login_fn)

    @classmethod
    async def from_existing_auth(
        cls,
        session: aiohttp.ClientSession,
        username: str,
        refresh_token: str,
        user_id: str,
        *,
        refresh_fn: Any = None,
    ) -> WinixAccount:
        """Create an account from a stored refresh token.

        refresh_fn can be provided to run the blocking auth in an executor.
        """
        if refresh_fn:
            auth = await refresh_fn(WinixAuth.refresh, refresh_token, user_id)
        else:
            auth = WinixAuth.refresh(refresh_token, user_id)

        return await cls._create(session, username, auth, executor_fn=refresh_fn)

    @classmethod
    async def _create(
        cls,
        session: aiohttp.ClientSession,
        username: str,
        auth: WinixAuthResponse,
        *,
        executor_fn: Any = None,
    ) -> WinixAccount:
        """Create account instance and run the Winix mobile handshake."""
        account = cls(session, username, auth, executor_fn=executor_fn)
        await account._establish_session()
        return account

    @property
    def auth(self) -> WinixAuthResponse:
        """Current auth response (for persisting tokens)."""
        return self._auth

    @property
    def identity_id(self) -> str:
        """Cognito Identity Pool identity id for the current user.

        Required to construct a WinixDeviceClient for device control.
        """
        if not self._identity_id:
            raise WinixApiError("identity_id not resolved; account has no active session")
        return self._identity_id

    async def get_devices(self) -> list[WinixDevice]:
        """Fetch the list of devices associated with this account."""
        response = await self._mobile_post(
            URL_GET_DEVICE_INFO_LIST,
            {
                "accessToken": await self._get_access_token(),
                "uuid": self._uuid,
                "osType": MOBILE_OS_TYPE,
                "osVersion": MOBILE_OS_VERSION,
                "mobileLang": MOBILE_LANG,
                "appVersion": MOBILE_APP_VERSION,
                "mobileModel": MOBILE_MODEL,
            },
        )

        devices: list[WinixDevice] = []
        for raw in response.get("deviceInfoList", []):
            devices.append(
                WinixDevice(
                    device_id=raw["deviceId"],
                    mac=raw.get("mac", ""),
                    device_alias=raw.get("deviceAlias", ""),
                    model_name=raw.get("modelName", ""),
                    mcu_ver=raw.get("mcuVer", ""),
                    wifi_ver=raw.get("wifiVer", ""),
                    device_loc_code=raw.get("deviceLocCode", ""),
                    filter_replace_date=raw.get("filterReplaceDate", ""),
                    filter_alarm_month=raw.get("filterAlarmMonth"),
                )
            )

        return devices

    async def _get_access_token(self) -> str:
        """Get a valid access token, refreshing if expired."""
        if self._is_expired():
            await self._refresh()
        return self._auth.access_token

    def _is_expired(self) -> bool:
        """Check if the access token is expired or close to expiring."""
        if not self._auth.access_token:
            return True
        return self._auth.expires_at <= (time.time() + TOKEN_EXPIRY_BUFFER_SECONDS)

    async def _refresh(self) -> None:
        """Refresh the access token and re-establish the mobile session."""
        _LOGGER.debug("account:refresh() token expired, refreshing")
        self._auth = await self._run_auth(
            WinixAuth.refresh, self._auth.refresh_token, self._auth.user_id
        )
        self._uuid = self._generate_uuid(self._auth.user_id)
        await self._establish_session()

    async def _run_auth(self, fn: Any, *args: Any) -> WinixAuthResponse:
        """Run a blocking auth function via the executor if provided."""
        if self._executor_fn:
            return await self._executor_fn(fn, *args)
        return fn(*args)

    async def _establish_session(self) -> None:
        """Run the Winix mobile handshake after a fresh login or token refresh.

        Order is load-bearing as of v1.5.7:
          1. Resolve Cognito identity id (needed by registerUser/checkAccessToken)
          2. registerUser
          3. init
          4. checkAccessToken
        """
        await self._resolve_identity_id()
        await self._register_user()
        await self._init()
        await self._check_access_token()

    async def _resolve_identity_id(self) -> None:
        """Resolve the Cognito Identity Pool identity id for the current user.

        Required in mobile API payloads and device control URLs as of v1.5.7.
        """
        response = await self._run_auth(self._get_identity_id_sync, self._auth.id_token)
        identity_id = response.get("IdentityId")
        if not identity_id:
            raise WinixApiError("Cognito GetId returned no IdentityId")
        self._identity_id = identity_id

    @staticmethod
    def _get_identity_id_sync(id_token: str) -> dict[str, Any]:
        """Blocking call to Cognito Identity GetId; run via executor."""
        client = boto3.client(
            "cognito-identity",
            region_name=COGNITO_REGION,
            config=BotoConfig(signature_version=UNSIGNED),
        )
        return client.get_id(
            IdentityPoolId=COGNITO_IDENTITY_POOL_ID,
            Logins={_COGNITO_LOGINS_PROVIDER: id_token},
        )

    async def _register_user(self) -> None:
        """Register this android UUID with the Winix backend.

        Must be called after resolving identity_id, before init/checkAccessToken.
        This is how the Winix backend associates our fake android device UUID
        with the user's account.
        """
        await self._mobile_post(
            URL_REGISTER_USER,
            {
                "identityId": self._identity_id,
                "accessToken": self._auth.access_token,
                "uuid": self._uuid,
                "email": self._username,
                "osType": MOBILE_OS_TYPE,
                "osVersion": MOBILE_OS_VERSION,
                "mobileLang": MOBILE_LANG,
                "appVersion": MOBILE_APP_VERSION,
                "mobileModel": MOBILE_MODEL,
            },
        )

    async def _init(self) -> None:
        """Winix mobile API init endpoint. Called after registerUser as of v1.5.7."""
        await self._mobile_post(
            URL_INIT,
            {
                "accessToken": self._auth.access_token,
                "uuid": self._uuid,
                "region": "US",
            },
        )

    async def _check_access_token(self) -> None:
        """Validate the access token with the Winix backend."""
        await self._mobile_post(
            URL_CHECK_ACCESS_TOKEN,
            {
                "identityId": self._identity_id,
                "accessToken": self._auth.access_token,
                "uuid": self._uuid,
                "osVersion": MOBILE_OS_VERSION,
                "mobileLang": MOBILE_LANG,
                "appVersion": MOBILE_APP_VERSION,
                "mobileModel": MOBILE_MODEL,
            },
        )

    async def _mobile_post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Send an encrypted POST to the Winix mobile API."""
        encrypted = encrypt(payload)

        async with self._session.post(
            url,
            data=encrypted,
            headers={
                "Content-Type": "application/octet-stream",
                "Accept": "application/octet-stream",
            },
        ) as resp:
            if resp.status != 200:
                raise WinixApiError(f"Mobile API error: {url} returned {resp.status}")
            data = await resp.read()

        response = decrypt(data)

        # Check for API-level errors
        result_code = str(response.get("resultCode", ""))
        if result_code and result_code not in ("", "0", "200"):
            raise WinixApiError(
                f"Mobile API error: {response.get('resultMessage', 'Unknown')}",
                result_code=result_code,
                result_message=response.get("resultMessage", ""),
            )

        return response

    @staticmethod
    def _generate_uuid(user_id: str) -> str:
        """Generate a fake android secure ID from the user's cognito subject.

        Formula: CRC32(UUID_PREFIX + user_id) + CRC32(UUID_SUFFIX + user_id)
        Returns a 16-character hex string.
        """
        if not user_id:
            return ""

        user_id_bytes = user_id.encode("utf-8")
        p1 = binascii.crc32(UUID_PREFIX + user_id_bytes) & 0xFFFFFFFF
        p2 = binascii.crc32(UUID_SUFFIX + user_id_bytes) & 0xFFFFFFFF
        return f"{p1:08x}{p2:08x}"
