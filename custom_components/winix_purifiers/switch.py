"""Switch entities for Winix purifiers (PlasmaWave, Child Lock)."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import Plasmawave
from .const import DOMAIN, LOGGER
from .coordinator import WinixPurifiersCoordinator
from .entity import WinixEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Winix switch entities."""
    coordinator: WinixPurifiersCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = []

    for device_id in coordinator.get_device_ids():
        device_data = coordinator.get_device_data(device_id)

        # PlasmaWave — always available on all models
        entities.append(WinixPlasmawaveSwitch(coordinator, device_id))

        # Child lock — model-dependent
        if device_data.capabilities.has_child_lock:
            entities.append(WinixChildLockSwitch(coordinator, device_id))

    async_add_entities(entities)


class WinixPlasmawaveSwitch(WinixEntity, SwitchEntity):
    """PlasmaWave ionizer toggle."""

    _attr_translation_key = "plasmawave"

    def __init__(
        self,
        coordinator: WinixPurifiersCoordinator,
        device_id: str,
    ) -> None:
        super().__init__(coordinator, device_id)
        mac = self._device_data.info.mac.lower()
        self._attr_unique_id = f"{DOMAIN}_{mac}_plasmawave"

    @property
    def is_on(self) -> bool:
        return self._device_data.status.plasmawave == Plasmawave.ON

    async def async_turn_on(self, **kwargs) -> None:
        LOGGER.debug("switch:plasmawave:turn_on()")
        client = self._device_data.client

        await self.coordinator.async_send_command(
            self._device_id,
            lambda: client.set_plasmawave(Plasmawave.ON),
            optimistic_update=lambda s: setattr(s, "plasmawave", Plasmawave.ON),
        )

    async def async_turn_off(self, **kwargs) -> None:
        LOGGER.debug("switch:plasmawave:turn_off()")
        client = self._device_data.client

        await self.coordinator.async_send_command(
            self._device_id,
            lambda: client.set_plasmawave(Plasmawave.OFF),
            optimistic_update=lambda s: setattr(s, "plasmawave", Plasmawave.OFF),
        )


class WinixChildLockSwitch(WinixEntity, SwitchEntity):
    """Child lock toggle (C610+)."""

    _attr_translation_key = "child_lock"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: WinixPurifiersCoordinator,
        device_id: str,
    ) -> None:
        super().__init__(coordinator, device_id)
        mac = self._device_data.info.mac.lower()
        self._attr_unique_id = f"{DOMAIN}_{mac}_child_lock"

    @property
    def is_on(self) -> bool:
        return self._device_data.status.child_lock == "1"

    async def async_turn_on(self, **kwargs) -> None:
        LOGGER.debug("switch:child_lock:turn_on()")
        client = self._device_data.client

        await self.coordinator.async_send_command(
            self._device_id,
            lambda: client.set_child_lock("1"),
            optimistic_update=lambda s: setattr(s, "child_lock", "1"),
        )

    async def async_turn_off(self, **kwargs) -> None:
        LOGGER.debug("switch:child_lock:turn_off()")
        client = self._device_data.client

        await self.coordinator.async_send_command(
            self._device_id,
            lambda: client.set_child_lock("0"),
            optimistic_update=lambda s: setattr(s, "child_lock", "0"),
        )
