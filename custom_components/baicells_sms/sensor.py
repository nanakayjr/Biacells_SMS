"""Sensor platform for Baicells SMS."""

from __future__ import annotations

import json
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_LOGO_PATH,
    CONF_MAX_ATTR_MESSAGES,
    DEFAULT_LOGO_PATH,
    DEFAULT_MAX_ATTR_MESSAGES,
    DEFAULT_NAME,
)
from .coordinator import BaicellsSmsCoordinator

# Home Assistant's recorder refuses to persist state attributes larger than
# 16384 bytes (see homeassistant/components/recorder/db_schema.py). Leave a
# safety margin below that hard limit for the rest of the attribute payload
# (last_update, file paths, etc.) and for JSON encoding overhead.
_MAX_MESSAGES_ATTR_BYTES = 12000


def _limit_messages_by_size(
    messages: list[dict[str, Any]], max_bytes: int
) -> list[dict[str, Any]]:
    """Keep as many (newest-first) messages as fit within ``max_bytes``.

    Guards against the recorder's 16384 byte attribute limit even when
    individual messages are unusually large (e.g. long concatenated SMS),
    regardless of how the ``max_attribute_messages`` option is configured.
    """
    limited: list[dict[str, Any]] = []
    total = 2  # account for the enclosing "[" "]"
    for message in messages:
        encoded_len = len(json.dumps(message, ensure_ascii=False, default=str)) + 1
        if limited and total + encoded_len > max_bytes:
            break
        limited.append(message)
        total += encoded_len
    return limited


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
        """Detailed SMS messages similar to a phone message list.

        Home Assistant's recorder will silently stop storing an entity's
        state attributes once they exceed 16384 bytes. Since the full SMS
        history grows without bound over time, only the most recent
        messages are exposed here - bounded both by count (configurable
        via the ``max_attribute_messages`` option) and by total encoded
        size - while the complete history remains available in the JSON
        history file on disk.
        """
        data = self.coordinator.data or {}
        merged = {**self.coordinator.entry.data, **self.coordinator.entry.options}
        max_messages = int(merged.get(CONF_MAX_ATTR_MESSAGES, DEFAULT_MAX_ATTR_MESSAGES))
        all_messages = data.get("messages", [])
        by_count = all_messages[:max_messages] if max_messages > 0 else all_messages
        limited_messages = _limit_messages_by_size(by_count, _MAX_MESSAGES_ATTR_BYTES)
        return {
            "messages": limited_messages,
            "messages_truncated": len(all_messages) > len(limited_messages),
            "last_poll_count": data.get("last_poll_count", 0),
            "new_message_count": data.get("new_message_count", 0),
            "last_update": data.get("last_update"),
            "messages_file": data.get("messages_file"),
            "history_file": data.get("history_file"),
            "delete_after_read": data.get("delete_after_read"),
            "logo_path": self.entity_picture,
        }
