"""Cognito SRP authentication for Winix accounts."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import boto3
from botocore import UNSIGNED
from botocore.config import Config as BotoConfig
from jose import jwt as jose_jwt
from warrant_lite import WarrantLite

from .const import (
    COGNITO_APP_CLIENT_ID,
    COGNITO_REGION,
    COGNITO_USER_POOL_ID,
)
from .exceptions import RefreshTokenExpiredError, WinixAuthError

_LOGGER = logging.getLogger(__name__)

_LOGIN_RETRY_DELAY_SECONDS = 3


@dataclass
class WinixAuthResponse:
    """Authentication response from Cognito."""

    user_id: str
    access_token: str
    id_token: str
    expires_at: float  # Unix timestamp (seconds)
    refresh_token: str


class WinixAuth:
    """Handles Cognito SRP authentication."""

    @staticmethod
    def login(
        username: str,
        password: str,
        max_attempts: int = 5,
    ) -> WinixAuthResponse:
        """Authenticate with Cognito using SRP.

        Retries on failure since Winix auth can be flaky when the user is
        logged in on another device simultaneously.
        """
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                return WinixAuth._do_login(username, password)
            except Exception as err:
                last_error = err
                _LOGGER.error(
                    "auth:login() attempt %d/%d failed: %s: %s",
                    attempt,
                    max_attempts,
                    type(err).__name__,
                    err,
                )
                if attempt < max_attempts:
                    time.sleep(_LOGIN_RETRY_DELAY_SECONDS)

        raise WinixAuthError(f"Login failed after {max_attempts} attempts") from last_error

    @staticmethod
    def refresh(refresh_token: str, user_id: str) -> WinixAuthResponse:
        """Refresh an expired access token."""
        client = boto3.client(
            "cognito-idp",
            region_name=COGNITO_REGION,
            config=BotoConfig(signature_version=UNSIGNED),
        )

        try:
            response = client.initiate_auth(
                ClientId=COGNITO_APP_CLIENT_ID,
                AuthFlow="REFRESH_TOKEN",
                AuthParameters={
                    "REFRESH_TOKEN": refresh_token,
                },
            )
        except client.exceptions.NotAuthorizedException as err:
            raise RefreshTokenExpiredError("Refresh token expired, re-login required") from err

        result = response["AuthenticationResult"]
        expires_in = result.get("ExpiresIn", 3600)

        return WinixAuthResponse(
            user_id=user_id,
            access_token=result["AccessToken"],
            id_token=result["IdToken"],
            expires_at=time.time() + expires_in,
            refresh_token=refresh_token,
        )

    @staticmethod
    def _do_login(username: str, password: str) -> WinixAuthResponse:
        """Single login attempt via Cognito SRP."""
        wl = WarrantLite(
            username=username,
            password=password,
            pool_id=COGNITO_USER_POOL_ID,
            client_id=COGNITO_APP_CLIENT_ID,
            client_secret=None,
            client=boto3.client(
                "cognito-idp",
                region_name=COGNITO_REGION,
                config=BotoConfig(signature_version=UNSIGNED),
            ),
        )

        tokens = wl.authenticate_user()
        auth_result = tokens["AuthenticationResult"]

        # Extract user_id from JWT "sub" claim
        claims = jose_jwt.get_unverified_claims(auth_result["AccessToken"])
        user_id = claims["sub"]
        expires_in = auth_result.get("ExpiresIn", 3600)

        return WinixAuthResponse(
            user_id=user_id,
            access_token=auth_result["AccessToken"],
            id_token=auth_result["IdToken"],
            expires_at=time.time() + expires_in,
            refresh_token=auth_result["RefreshToken"],
        )
