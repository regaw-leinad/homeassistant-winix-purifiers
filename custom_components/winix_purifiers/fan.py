"""Fan entity for Winix air purifiers."""

from __future__ import annotations

import asyncio

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .api import Airflow, DeviceStatus, Mode, Plasmawave, Power
from .const import (
    COMMAND_DELAY_SECONDS,
    DOMAIN,
    LOGGER,
    ORDERED_AIRFLOW_SPEEDS,
    PRESET_AUTO,
    PRESET_MODES,
    PRESET_SLEEP,
)
from .coordinator import WinixPurifiersCoordinator
from .entity import WinixEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Winix fan entities."""
    coordinator: WinixPurifiersCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        WinixFan(coordinator, device_id) for device_id in coordinator.get_device_ids()
    )


class WinixFan(WinixEntity, FanEntity):
    """Represents a Winix air purifier as a fan entity."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_speed_count = len(ORDERED_AIRFLOW_SPEEDS)
    _attr_preset_modes = PRESET_MODES

    def __init__(
        self,
        coordinator: WinixPurifiersCoordinator,
        device_id: str,
    ) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{DOMAIN}_{self._device_data.info.mac.lower()}"

    @property
    def name(self) -> str | None:
        # Primary entity — uses the device name
        return None

    @property
    def is_on(self) -> bool:
        return self._device_data.status.power == Power.ON

    @property
    def percentage(self) -> int | None:
        status = self._device_data.status

        if status.power == Power.OFF:
            return 0

        if status.airflow == Airflow.SLEEP:
            return None

        return ordered_list_item_to_percentage(ORDERED_AIRFLOW_SPEEDS, status.airflow)

    @property
    def preset_mode(self) -> str | None:
        status = self._device_data.status

        if status.power == Power.OFF:
            return None
        if status.mode == Mode.AUTO:
            return PRESET_AUTO
        if status.airflow == Airflow.SLEEP:
            return PRESET_SLEEP

        return None

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs,
    ) -> None:
        """Turn on the purifier, optionally setting speed or preset."""
        LOGGER.debug("fan:async_turn_on(pct=%s, preset=%s)", percentage, preset_mode)

        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
            return

        if percentage is not None:
            await self.async_set_percentage(percentage)
            return

        # Just turn on
        client = self._device_data.client

        await self.coordinator.async_send_command(
            self._device_id,
            lambda: client.set_power(Power.ON),
            optimistic_update=lambda s: _apply_power_on(s),
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the purifier."""
        LOGGER.debug("fan:async_turn_off()")
        client = self._device_data.client

        await self.coordinator.async_send_command(
            self._device_id,
            lambda: client.set_power(Power.OFF),
            optimistic_update=lambda s: _apply_power_off(s),
        )

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the fan speed percentage."""
        LOGGER.debug("fan:async_set_percentage(%d)", percentage)

        if percentage == 0:
            await self.async_turn_off()
            return

        airflow = percentage_to_ordered_list_item(ORDERED_AIRFLOW_SPEEDS, percentage)
        await self._set_airflow(airflow)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set a preset mode (Auto or Sleep)."""
        LOGGER.debug("fan:async_set_preset_mode(%s)", preset_mode)
        client = self._device_data.client
        status = self._device_data.status

        # Ensure device is on first
        if status.power == Power.OFF:
            await self.coordinator.async_send_command(
                self._device_id,
                lambda: client.set_power(Power.ON),
                optimistic_update=lambda s: _apply_power_on(s),
            )

        if preset_mode == PRESET_AUTO:
            await self.coordinator.async_send_command(
                self._device_id,
                lambda: client.set_mode(Mode.AUTO),
                optimistic_update=lambda s: _apply_auto(s),
            )
            return

        if preset_mode == PRESET_SLEEP:
            # Sleep requires manual mode + sleep airflow with a delay between
            if status.mode != Mode.MANUAL:
                await self.coordinator.async_send_command(
                    self._device_id,
                    lambda: client.set_mode(Mode.MANUAL),
                    optimistic_update=lambda s: setattr(s, "mode", Mode.MANUAL),
                )
                await asyncio.sleep(COMMAND_DELAY_SECONDS)

            await self.coordinator.async_send_command(
                self._device_id,
                lambda: client.set_airflow(Airflow.SLEEP),
                optimistic_update=lambda s: _apply_sleep(s),
            )

    async def _set_airflow(self, airflow: Airflow) -> None:
        """Set airflow speed, auto-switching to manual mode if needed."""
        client = self._device_data.client
        status = self._device_data.status

        # Optimistically set the final desired state immediately so the UI
        # doesn't flash intermediate values during the command sequence
        def _apply_final(s: DeviceStatus) -> None:
            s.power = Power.ON
            s.mode = Mode.MANUAL
            s.airflow = airflow

        # Ensure device is on (no optimistic update — we'll push final state at the end)
        if status.power == Power.OFF:
            await self.coordinator.async_send_command(
                self._device_id,
                lambda: client.set_power(Power.ON),
            )

        # Device needs manual mode to accept airflow commands.
        # Must delay between mode and airflow or the airflow command
        # gets dropped by the device.
        if status.mode != Mode.MANUAL:
            await self.coordinator.async_send_command(
                self._device_id,
                lambda: client.set_mode(Mode.MANUAL),
                # Push the final state now so the UI shows the target speed immediately
                optimistic_update=_apply_final,
            )
            await asyncio.sleep(COMMAND_DELAY_SECONDS)

        await self.coordinator.async_send_command(
            self._device_id,
            lambda: client.set_airflow(airflow),
            optimistic_update=_apply_final,
        )


# Side effects observed from device testing
def _apply_power_on(status: DeviceStatus) -> None:
    status.power = Power.ON
    status.plasmawave = Plasmawave.ON


def _apply_power_off(status: DeviceStatus) -> None:
    status.power = Power.OFF
    status.mode = Mode.AUTO
    status.plasmawave = Plasmawave.OFF


def _apply_auto(status: DeviceStatus) -> None:
    status.mode = Mode.AUTO
    status.airflow = Airflow.LOW


def _apply_sleep(status: DeviceStatus) -> None:
    status.airflow = Airflow.SLEEP
    status.plasmawave = Plasmawave.OFF
