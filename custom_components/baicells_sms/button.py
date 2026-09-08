"""Button platform for Baicells SMS."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME
from .coordinator import BaicellsSmsCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Baicells SMS button entities."""
    coordinator: BaicellsSmsCoordinator = hass.data["baicells_sms"]["coordinators"][entry.entry_id]
    async_add_entities([BaicellsSmsReadNowButton(coordinator, entry)])


class BaicellsSmsReadNowButton(CoordinatorEntity[BaicellsSmsCoordinator], ButtonEntity):
    """Button to force SMS polling."""

    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: BaicellsSmsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_force_read"
        self._attr_name = f"{DEFAULT_NAME} Force Read"

    async def async_press(self) -> None:
        """Trigger an immediate SMS read."""
        await self.coordinator.async_request_refresh()
