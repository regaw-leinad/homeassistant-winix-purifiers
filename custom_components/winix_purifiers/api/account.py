"""Winix account management, device listing and token lifecycle."""

from __future__ import annotations

import binascii
import logging
import time
from typing import Any

import aiohttp

from .auth import WinixAuth, WinixAuthResponse
from .const import (
    COGNITO_CLIENT_SECRET_KEY,
    MOBILE_APP_VERSION,
    MOBILE_LANG,
    MOBILE_MODEL,
    MOBILE_OS_TYPE,
    MOBILE_OS_VERSION,
    TOKEN_EXPIRY_BUFFER_SECONDS,
    URL_CHECK_ACCESS_TOKEN,
    URL_GET_DEVICE_INFO_LIST,
    URL_REGISTER_USER,
    UUID_PREFIX,
    UUID_SUFFIX,
)
from .crypto import decrypt, encrypt
from .device import WinixDevice
from .exceptions import WinixApiError

_LOGGER = logging.getLogger(__name__)


class WinixAccount:
    """Manages a Winix account session with encrypted mobile API calls."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        auth: WinixAuthResponse,
    ) -> None:
        self._session = session
        self._username = username
        self._auth = auth
        self._uuid = self._generate_uuid(auth.user_id)

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

        return await cls._create(session, username, auth)

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

        return await cls._create(session, username, auth)

    @classmethod
    async def _create(
        cls,
        session: aiohttp.ClientSession,
        username: str,
        auth: WinixAuthResponse,
    ) -> WinixAccount:
        """Create account instance and register with Winix backend."""
        account = cls(session, username, auth)
        await account._register_user()
        await account._check_access_token()
        return account

    @property
    def auth(self) -> WinixAuthResponse:
        """Current auth response (for persisting tokens)."""
        return self._auth

    async def get_devices(self) -> list[WinixDevice]:
        """Fetch the list of devices associated with this account."""
        response = await self._mobile_post(
            URL_GET_DEVICE_INFO_LIST,
            {
                "cognitoClientSecretKey": COGNITO_CLIENT_SECRET_KEY,
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
        """Refresh the access token."""
        _LOGGER.debug("account:refresh() token expired, refreshing")
        self._auth = WinixAuth.refresh(self._auth.refresh_token, self._auth.user_id)
        self._uuid = self._generate_uuid(self._auth.user_id)
        await self._register_user()
        await self._check_access_token()

    async def _register_user(self) -> None:
        """Register this android UUID with the Winix backend.

        Must be called after getting a cognito token, before checkAccessToken.
        This is how the Winix backend associates our fake android device UUID
        with the user's account.
        """
        await self._mobile_post(
            URL_REGISTER_USER,
            {
                "cognitoClientSecretKey": COGNITO_CLIENT_SECRET_KEY,
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

    async def _check_access_token(self) -> None:
        """Validate the access token with the Winix backend."""
        await self._mobile_post(
            URL_CHECK_ACCESS_TOKEN,
            {
                "cognitoClientSecretKey": COGNITO_CLIENT_SECRET_KEY,
                "accessToken": self._auth.access_token,
                "uuid": self._uuid,
                "osType": MOBILE_OS_TYPE,
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
