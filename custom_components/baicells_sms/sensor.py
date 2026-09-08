"""Sensor platform for Baicells SMS."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_LOGO_PATH, DEFAULT_LOGO_PATH, DEFAULT_NAME
from .coordinator import BaicellsSmsCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Baicells SMS sensor entities."""
    coordinator: BaicellsSmsCoordinator = hass.data["baicells_sms"]["coordinators"][entry.entry_id]
    async_add_entities([BaicellsSmsInboxSensor(coordinator, entry)])


class BaicellsSmsInboxSensor(CoordinatorEntity[BaicellsSmsCoordinator], SensorEntity):
    """Expose SIM inbox message data."""

    _attr_icon = "mdi:message-text"
    _attr_translation_key = "inbox"

    def __init__(self, coordinator: BaicellsSmsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_inbox"

    @property
    def native_value(self) -> int:
        """Total number of stored messages."""
        if not self.coordinator.data:
            return 0
        return int(self.coordinator.data.get("message_count", 0))

    @property
    def entity_picture(self) -> str | None:
        """Return optional logo path for UI display."""
        merged = {**self.coordinator.entry.data, **self.coordinator.entry.options}
        logo_path = merged.get(CONF_LOGO_PATH, DEFAULT_LOGO_PATH)
        if not logo_path:
            return None
        return str(logo_path)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Detailed SMS messages similar to a phone message list."""
        data = self.coordinator.data or {}
        return {
            "messages": data.get("messages", []),
            "last_poll_count": data.get("last_poll_count", 0),
            "new_message_count": data.get("new_message_count", 0),
            "last_update": data.get("last_update"),
            "messages_file": data.get("messages_file"),
            "history_file": data.get("history_file"),
            "delete_after_read": data.get("delete_after_read"),
            "logo_path": self.entity_picture,
        }
