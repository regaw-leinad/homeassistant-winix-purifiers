"""Winix Air Purifiers integration for Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    DeviceStatus,
    ModelCapabilities,
    RefreshTokenExpiredError,
    WinixAccount,
    WinixApiError,
    WinixDeviceClient,
)
from .config_flow import CONF_REFRESH_TOKEN, CONF_USER_ID
from .const import DOMAIN, LOGGER
from .coordinator import WinixDeviceCoordinator, WinixDeviceData

PLATFORMS = [
    Platform.FAN,
    Platform.SWITCH,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Winix Purifiers from a config entry."""
    session = async_get_clientsession(hass)

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    refresh_token = entry.data.get(CONF_REFRESH_TOKEN, "")
    user_id = entry.data.get(CONF_USER_ID, "")

    # Try existing refresh token first, fall back to full login
    account = await _create_account(hass, session, username, password, refresh_token, user_id)

    # Fetch device list
    try:
        devices = await account.get_devices()
    except WinixApiError as err:
        raise ConfigEntryNotReady(f"Failed to fetch devices: {err}") from err

    if not devices:
        LOGGER.warning("init:async_setup_entry() no devices found for %s", username)

    # Persist updated tokens
    new_auth = account.auth
    hass.config_entries.async_update_entry(
        entry,
        data={
            **entry.data,
            CONF_REFRESH_TOKEN: new_auth.refresh_token,
            CONF_USER_ID: new_auth.user_id,
        },
    )

    # Create a per-device coordinator for each device
    coordinators: dict[str, WinixDeviceCoordinator] = {}
    for device in devices:
        client = WinixDeviceClient(session, device.device_id)

        # Initial status fetch to detect model capabilities
        raw_attributes: dict[str, str] = {}
        try:
            raw_attributes = await client.get_raw_attributes()
        except Exception:
            LOGGER.debug(
                "init:async_setup_entry() failed initial status for %s",
                device.device_alias,
            )

        device.raw_attributes = raw_attributes
        capabilities = ModelCapabilities(
            model_name=device.model_name,
            available_attributes=set(raw_attributes.keys()),
        )

        device_data = WinixDeviceData(
            info=device,
            status=DeviceStatus(
                power="0",
                mode="01",
                airflow="01",
                air_quality="01",
                plasmawave="0",
                filter_hours=0,
            ),
            capabilities=capabilities,
            client=client,
        )

        coordinator = WinixDeviceCoordinator(hass, device_data)
        await coordinator.async_config_entry_first_refresh()
        coordinators[device.device_id] = coordinator

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinators
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _create_account(
    hass: HomeAssistant,
    session,
    username: str,
    password: str,
    refresh_token: str,
    user_id: str,
) -> WinixAccount:
    """Create a WinixAccount, trying refresh token first then full login."""
    if refresh_token and user_id:
        try:
            return await WinixAccount.from_existing_auth(
                session,
                username,
                refresh_token,
                user_id,
                refresh_fn=hass.async_add_executor_job,
            )
        except RefreshTokenExpiredError:
            LOGGER.debug("init:_create_account() refresh token expired, re-logging in")
        except Exception:
            LOGGER.debug("init:_create_account() refresh failed, trying full login")

    try:
        return await WinixAccount.from_credentials(
            session,
            username,
            password,
            login_fn=hass.async_add_executor_job,
        )
    except Exception as err:
        raise ConfigEntryAuthFailed("Failed to authenticate with Winix") from err
