"""Git Sync: commit and push the Home Assistant configuration, export dashboards."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import CoreState, Event, HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_change, async_track_time_interval
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import (
    CARD_URL,
    CONF_COMMIT_INTERVAL,
    CONF_EXPORT_ENABLED,
    CONF_EXPORT_TIME,
    DEFAULT_COMMIT_INTERVAL,
    DEFAULT_EXPORT_TIME,
    DOMAIN,
    VERSION,
)
from .coordinator import GitSyncCoordinator
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type GitSyncConfigEntry = ConfigEntry[GitSyncCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the card, load it on every dashboard and register the actions."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(Path(__file__).parent / "frontend" / "git-sync-card.js"), True)]
    )

    async def _register(_: Event | None = None) -> None:
        if not await _async_register_resource(hass):
            # Dashboard resources in YAML mode: load the card on every page instead.
            add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")

    if hass.state is CoreState.running:
        await _register()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _register)

    async_setup_services(hass)
    return True


def _storage_resources(hass: HomeAssistant) -> Any | None:
    """Return the dashboard resources collection when it is editable from the UI.

    hass.data["lovelace"] is a dict before 2025.2, then a dataclass whose `mode` field became `resource_mode` in 2026.2.
    """
    lovelace = hass.data.get("lovelace")
    if isinstance(lovelace, dict):
        mode, resources = lovelace.get("resource_mode", lovelace.get("mode")), lovelace.get("resources")
    else:
        mode = getattr(lovelace, "resource_mode", getattr(lovelace, "mode", None))
        resources = getattr(lovelace, "resources", None)
    return resources if mode == "storage" else None


async def _async_register_resource(hass: HomeAssistant) -> bool:
    """Add or update the card in Settings → Dashboards → Resources."""
    resources = _storage_resources(hass)
    if resources is None:
        return False
    url = f"{CARD_URL}?v={VERSION}"
    try:
        await resources.async_get_info()  # loads the collection from storage
        existing = [item for item in resources.async_items() if item.get("url", "").split("?")[0] == CARD_URL]
        if not existing:
            await resources.async_create_item({"res_type": "module", "url": url})
            return True
        if existing[0]["url"] != url:
            await resources.async_update_item(existing[0]["id"], {"res_type": "module", "url": url})
        for duplicate in existing[1:]:
            await resources.async_delete_item(duplicate["id"])
    except Exception:  # noqa: BLE001 - never block the integration on the card
        _LOGGER.exception("Could not register the Git Sync card as a dashboard resource")
        return False
    return True


async def async_setup_entry(hass: HomeAssistant, entry: GitSyncConfigEntry) -> bool:
    """Set up a repository from a config entry."""
    if hass.state is CoreState.running:
        # async_setup runs once per start: after the last entry was removed (which drops the card resource)
        # and one is added again, the resource has to come back without a restart.
        await _async_register_resource(hass)
    coordinator = GitSyncCoordinator(hass, entry)
    await coordinator.async_load()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    _schedule(hass, entry, coordinator)
    entry.async_on_unload(entry.add_update_listener(_async_reload))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GitSyncConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: GitSyncConfigEntry) -> None:
    """Drop the saved push/export times, and the card resource once the last repository is removed."""
    await GitSyncCoordinator.async_remove_store(hass, entry)
    others = [e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id != entry.entry_id]
    if others or (resources := _storage_resources(hass)) is None:
        return
    for item in list(resources.async_items()):
        if item.get("url", "").split("?")[0] == CARD_URL:
            await resources.async_delete_item(item["id"])


async def _async_reload(hass: HomeAssistant, entry: GitSyncConfigEntry) -> None:
    """Reload when the options change."""
    await hass.config_entries.async_reload(entry.entry_id)


def _schedule(hass: HomeAssistant, entry: GitSyncConfigEntry, coordinator: GitSyncCoordinator) -> None:
    """Register the automatic commit interval and the daily dashboard export."""
    settings = coordinator.settings

    interval = int(settings.get(CONF_COMMIT_INTERVAL, DEFAULT_COMMIT_INTERVAL))
    if interval > 0:

        async def _auto_commit(_now: datetime) -> None:
            await coordinator.async_request_refresh()
            if not coordinator.dirty:
                return
            try:
                await coordinator.async_commit_push()
            except Exception:
                _LOGGER.exception("Automatic commit failed")

        entry.async_on_unload(
            async_track_time_interval(hass, _auto_commit, timedelta(minutes=interval), name=f"{DOMAIN} auto commit")
        )

    if settings.get(CONF_EXPORT_ENABLED, True):
        export_time = dt_util.parse_time(settings.get(CONF_EXPORT_TIME) or DEFAULT_EXPORT_TIME)
        if export_time is None:
            _LOGGER.warning("Invalid export time %s", settings.get(CONF_EXPORT_TIME))
            return

        async def _auto_export(_now: datetime) -> None:
            try:
                await coordinator.async_export_dashboards()
            except Exception:
                _LOGGER.exception("Automatic dashboard export failed")

        entry.async_on_unload(
            async_track_time_change(
                hass,
                _auto_export,
                hour=export_time.hour,
                minute=export_time.minute,
                second=export_time.second,
            )
        )
