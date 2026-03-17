"""Select entities for Winix purifiers (Brightness, Timer)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, LOGGER
from .coordinator import WinixPurifiersCoordinator
from .entity import WinixEntity

_BRIGHTNESS_OPTIONS = ["Off", "Low", "Medium", "High"]
_BRIGHTNESS_TO_VALUE = {"Off": "0", "Low": "30", "Medium": "70", "High": "100"}
_VALUE_TO_BRIGHTNESS = {v: k for k, v in _BRIGHTNESS_TO_VALUE.items()}

_TIMER_OPTIONS = ["Off", "1 hour", "2 hours", "4 hours", "8 hours", "12 hours"]
_TIMER_TO_VALUE = {
    "Off": "0",
    "1 hour": "1",
    "2 hours": "2",
    "4 hours": "4",
    "8 hours": "8",
    "12 hours": "12",
}
_VALUE_TO_TIMER = {v: k for k, v in _TIMER_TO_VALUE.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Winix select entities."""
    coordinator: WinixPurifiersCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SelectEntity] = []

    for device_id in coordinator.get_device_ids():
        device_data = coordinator.get_device_data(device_id)
        caps = device_data.capabilities

        if caps.has_brightness:
            entities.append(WinixBrightnessSelect(coordinator, device_id))
        if caps.has_timer:
            entities.append(WinixTimerSelect(coordinator, device_id))

    async_add_entities(entities)


class WinixBrightnessSelect(WinixEntity, SelectEntity):
    """Display brightness control (C610+)."""

    _attr_translation_key = "display_brightness"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = _BRIGHTNESS_OPTIONS

    def __init__(self, coordinator: WinixPurifiersCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        mac = self._device_data.info.mac.lower()
        self._attr_unique_id = f"{DOMAIN}_{mac}_brightness"

    @property
    def current_option(self) -> str | None:
        raw = self._device_data.status.brightness
        return _VALUE_TO_BRIGHTNESS.get(raw or "", "Off")

    async def async_select_option(self, option: str) -> None:
        LOGGER.debug("select:brightness:select_option(%s)", option)
        value = _BRIGHTNESS_TO_VALUE.get(option, "0")
        client = self._device_data.client

        await self.coordinator.async_send_command(
            self._device_id,
            lambda: client.set_brightness(value),
            optimistic_update=lambda s: setattr(s, "brightness", value),
        )


class WinixTimerSelect(WinixEntity, SelectEntity):
    """Power-off timer control (Tower XQ)."""

    _attr_translation_key = "timer"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = _TIMER_OPTIONS

    def __init__(self, coordinator: WinixPurifiersCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        mac = self._device_data.info.mac.lower()
        self._attr_unique_id = f"{DOMAIN}_{mac}_timer"

    @property
    def current_option(self) -> str | None:
        raw = self._device_data.status.timer
        if raw is None:
            return "Off"
        return _VALUE_TO_TIMER.get(str(raw), "Off")

    async def async_select_option(self, option: str) -> None:
        LOGGER.debug("select:timer:select_option(%s)", option)
        value = _TIMER_TO_VALUE.get(option, "0")
        client = self._device_data.client

        await self.coordinator.async_send_command(
            self._device_id,
            lambda: client.set_timer(value),
            optimistic_update=lambda s: setattr(s, "timer", int(value)),
        )
