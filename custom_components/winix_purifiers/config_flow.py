"""Config flow for Winix Purifiers."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .api import WinixAuth, WinixAuthError
from .const import DOMAIN, LOGGER

CONF_USER_ID = "user_id"
CONF_REFRESH_TOKEN = "refresh_token"

AUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

REAUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PASSWORD): str,
    }
)


class WinixPurifiersConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow for Winix Purifiers."""

    VERSION = 1

    _reauth_username: str | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial user setup step."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=AUTH_SCHEMA)

        errors: dict[str, str] = {}

        username = user_input[CONF_USERNAME]
        password = user_input[CONF_PASSWORD]

        try:
            auth = await self.hass.async_add_executor_job(WinixAuth.login, username, password)
        except WinixAuthError as err:
            LOGGER.error("config_flow:async_step_user() auth error: %s", err)
            errors["base"] = "invalid_auth"
            return self.async_show_form(step_id="user", data_schema=AUTH_SCHEMA, errors=errors)
        except Exception as err:
            LOGGER.exception("config_flow:async_step_user() unexpected error: %s", err)
            errors["base"] = "unknown"
            return self.async_show_form(step_id="user", data_schema=AUTH_SCHEMA, errors=errors)

        await self.async_set_unique_id(username.lower())
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=username,
            data={
                CONF_USERNAME: username,
                CONF_PASSWORD: password,
                CONF_USER_ID: auth.user_id,
                CONF_REFRESH_TOKEN: auth.refresh_token,
            },
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle reauth when token expires."""
        self._reauth_username = entry_data.get(CONF_USERNAME)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth password re-entry."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=REAUTH_SCHEMA,
                description_placeholders={"username": self._reauth_username or ""},
            )

        errors: dict[str, str] = {}
        password = user_input[CONF_PASSWORD]

        try:
            auth = await self.hass.async_add_executor_job(
                WinixAuth.login, self._reauth_username, password
            )
        except WinixAuthError:
            errors["base"] = "invalid_auth"
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=REAUTH_SCHEMA,
                errors=errors,
            )
        except Exception:
            LOGGER.exception("config_flow:reauth_confirm() unexpected error")
            errors["base"] = "unknown"
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=REAUTH_SCHEMA,
                errors=errors,
            )

        reauth_entry = self._get_reauth_entry()
        return self.async_update_reload_and_abort(
            reauth_entry,
            data={
                CONF_USERNAME: self._reauth_username,
                CONF_PASSWORD: password,
                CONF_USER_ID: auth.user_id,
                CONF_REFRESH_TOKEN: auth.refresh_token,
            },
        )
