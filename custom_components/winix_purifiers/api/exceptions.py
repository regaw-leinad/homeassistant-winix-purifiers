"""Winix API exceptions."""


class WinixError(Exception):
    """Base exception for Winix API errors."""


class WinixAuthError(WinixError):
    """Authentication error."""


class RefreshTokenExpiredError(WinixAuthError):
    """Refresh token has expired, re-login required."""


class WinixApiError(WinixError):
    """API call returned an error response."""

    def __init__(
        self,
        message: str,
        result_code: str = "",
        result_message: str = "",
    ) -> None:
        super().__init__(message)
        self.result_code = result_code
        self.result_message = result_message
