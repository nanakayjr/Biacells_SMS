"""Baicells SMS integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, PLATFORMS, SERVICE_FORCE_READ
from .coordinator import BaicellsSmsCoordinator

_LOGGER = logging.getLogger(__name__)

# Home Assistant's public ``homeassistant.const`` module does not export an
# ``ATTR_ENTRY_ID`` constant, so the service field name is defined locally.
ATTR_ENTRY_ID = "entry_id"

SERVICE_FORCE_READ_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTRY_ID): str})

_CARD_URL_PATH = "/baicells_sms/baicells-sms-card.js"
_CARD_FILE = Path(__file__).parent / "www" / "baicells-sms-card.js"


async def _async_register_frontend_card(hass: HomeAssistant) -> None:
    """Serve the bundled Lovelace card and auto-load it on every dashboard.

    This only needs to happen once per Home Assistant run, regardless of how
    many Baicells SMS config entries are set up, so it is guarded by a flag
    stored in ``hass.data``.
    """
    if hass.data.get(DOMAIN, {}).get("frontend_registered"):
        return

    try:
        try:
            # Home Assistant 2024.7+ prefers the async, non-deprecated API.
            from homeassistant.components.http import StaticPathConfig

            await hass.http.async_register_static_paths(
                [StaticPathConfig(_CARD_URL_PATH, str(_CARD_FILE), cache_headers=False)]
            )
        except ImportError:
            # Fall back for older Home Assistant cores.
            hass.http.register_static_path(_CARD_URL_PATH, str(_CARD_FILE), cache_headers=False)

        add_extra_js_url(hass, _CARD_URL_PATH)
    except Exception as err:  # noqa: BLE001 - never block setup on card errors
        _LOGGER.warning("Baicells SMS: unable to register the custom Lovelace card: %s", err)
        return

    hass.data.setdefault(DOMAIN, {})["frontend_registered"] = True


async def _async_handle_force_read(hass: HomeAssistant, call: ServiceCall) -> None:
    data: Mapping[str, Any] = call.data
    target_entry_id = data.get(ATTR_ENTRY_ID)
    coordinators: dict[str, BaicellsSmsCoordinator] = hass.data[DOMAIN]["coordinators"]

    if target_entry_id:
        coordinator = coordinators.get(target_entry_id)
        if coordinator is None:
            raise HomeAssistantError(f"Entry {target_entry_id} is not loaded")
        await coordinator.async_request_refresh()
        return

    for coordinator in coordinators.values():
        await coordinator.async_request_refresh()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Baicells SMS from a config entry."""
    hass.data.setdefault(DOMAIN, {"coordinators": {}})

    await _async_register_frontend_card(hass)

    coordinator = BaicellsSmsCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    hass.data[DOMAIN]["coordinators"][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, SERVICE_FORCE_READ):
        async def _service_handler(call: ServiceCall) -> None:
            await _async_handle_force_read(hass, call)

        hass.services.async_register(
            DOMAIN,
            SERVICE_FORCE_READ,
            _service_handler,
            schema=SERVICE_FORCE_READ_SCHEMA,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    coordinators: dict[str, BaicellsSmsCoordinator] = hass.data[DOMAIN]["coordinators"]
    coordinators.pop(entry.entry_id, None)

    if not coordinators and hass.services.has_service(DOMAIN, SERVICE_FORCE_READ):
        hass.services.async_remove(DOMAIN, SERVICE_FORCE_READ)

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
