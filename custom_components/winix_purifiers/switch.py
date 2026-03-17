"""Switch entities for Winix purifiers."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import Plasmawave
from .const import DOMAIN, LOGGER
from .coordinator import WinixDeviceCoordinator
from .entity import WinixEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Winix switch entities."""
    coordinators: dict[str, WinixDeviceCoordinator] = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = []

    for coordinator in coordinators.values():
        caps = coordinator.data.capabilities

        if caps.has_plasmawave:
            entities.append(WinixPlasmawaveSwitch(coordinator))
        if caps.has_child_lock:
            entities.append(WinixChildLockSwitch(coordinator))
        if caps.has_pollution_lamp:
            entities.append(WinixPollutionLampSwitch(coordinator))
        if caps.has_uv:
            entities.append(WinixUVSwitch(coordinator))

    async_add_entities(entities)


class WinixPlasmawaveSwitch(WinixEntity, SwitchEntity):
    """PlasmaWave ionizer toggle."""

    _attr_translation_key = "plasmawave"

    def __init__(self, coordinator: WinixDeviceCoordinator) -> None:
        super().__init__(coordinator)
        mac = self.device_data.info.mac.lower()
        self._attr_unique_id = f"{DOMAIN}_{mac}_plasmawave"

    @property
    def is_on(self) -> bool:
        return self.device_data.status.plasmawave == Plasmawave.ON

    async def async_turn_on(self, **kwargs) -> None:
        LOGGER.debug("switch:plasmawave:turn_on()")
        client = self.device_data.client

        await self.coordinator.async_send_command(
            lambda: client.set_plasmawave(Plasmawave.ON),
            optimistic_update=lambda s: setattr(s, "plasmawave", Plasmawave.ON),
        )

    async def async_turn_off(self, **kwargs) -> None:
        LOGGER.debug("switch:plasmawave:turn_off()")
        client = self.device_data.client

        await self.coordinator.async_send_command(
            lambda: client.set_plasmawave(Plasmawave.OFF),
            optimistic_update=lambda s: setattr(s, "plasmawave", Plasmawave.OFF),
        )


class WinixChildLockSwitch(WinixEntity, SwitchEntity):
    """Child lock toggle."""

    _attr_translation_key = "child_lock"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: WinixDeviceCoordinator) -> None:
        super().__init__(coordinator)
        mac = self.device_data.info.mac.lower()
        self._attr_unique_id = f"{DOMAIN}_{mac}_child_lock"

    @property
    def is_on(self) -> bool:
        return self.device_data.status.child_lock == "1"

    async def async_turn_on(self, **kwargs) -> None:
        LOGGER.debug("switch:child_lock:turn_on()")
        client = self.device_data.client

        await self.coordinator.async_send_command(
            lambda: client.set_child_lock("1"),
            optimistic_update=lambda s: setattr(s, "child_lock", "1"),
        )

    async def async_turn_off(self, **kwargs) -> None:
        LOGGER.debug("switch:child_lock:turn_off()")
        client = self.device_data.client

        await self.coordinator.async_send_command(
            lambda: client.set_child_lock("0"),
            optimistic_update=lambda s: setattr(s, "child_lock", "0"),
        )


class WinixPollutionLampSwitch(WinixEntity, SwitchEntity):
    """Pollution lamp (AQI indicator LED) toggle."""

    _attr_translation_key = "pollution_lamp"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: WinixDeviceCoordinator) -> None:
        super().__init__(coordinator)
        mac = self.device_data.info.mac.lower()
        self._attr_unique_id = f"{DOMAIN}_{mac}_pollution_lamp"

    @property
    def is_on(self) -> bool:
        return self.device_data.status.pollution_lamp == "1"

    async def async_turn_on(self, **kwargs) -> None:
        LOGGER.debug("switch:pollution_lamp:turn_on()")
        client = self.device_data.client

        await self.coordinator.async_send_command(
            lambda: client.set_pollution_lamp("1"),
            optimistic_update=lambda s: setattr(s, "pollution_lamp", "1"),
        )

    async def async_turn_off(self, **kwargs) -> None:
        LOGGER.debug("switch:pollution_lamp:turn_off()")
        client = self.device_data.client

        await self.coordinator.async_send_command(
            lambda: client.set_pollution_lamp("0"),
            optimistic_update=lambda s: setattr(s, "pollution_lamp", "0"),
        )


class WinixUVSwitch(WinixEntity, SwitchEntity):
    """UV sterilization toggle."""

    _attr_translation_key = "uv"

    def __init__(self, coordinator: WinixDeviceCoordinator) -> None:
        super().__init__(coordinator)
        mac = self.device_data.info.mac.lower()
        self._attr_unique_id = f"{DOMAIN}_{mac}_uv"

    @property
    def is_on(self) -> bool:
        return self.device_data.status.uv == "1"

    async def async_turn_on(self, **kwargs) -> None:
        LOGGER.debug("switch:uv:turn_on()")
        client = self.device_data.client

        await self.coordinator.async_send_command(
            lambda: client.set_uv("1"),
            optimistic_update=lambda s: setattr(s, "uv", "1"),
        )

    async def async_turn_off(self, **kwargs) -> None:
        LOGGER.debug("switch:uv:turn_off()")
        client = self.device_data.client

        await self.coordinator.async_send_command(
            lambda: client.set_uv("0"),
            optimistic_update=lambda s: setattr(s, "uv", "0"),
        )
