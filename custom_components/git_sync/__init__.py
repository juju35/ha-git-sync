"""Git Sync: commit and push the Home Assistant configuration, export dashboards."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_change, async_track_time_interval
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import (
    CARD_FILENAME,
    CARD_URL_BASE,
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
    """Serve the bundled Lovelace card and register the services."""
    async_setup_services(hass)

    frontend_dir = Path(__file__).parent / "frontend"
    if not await hass.async_add_executor_job((frontend_dir / CARD_FILENAME).is_file):
        _LOGGER.warning("Card bundle %s missing, the card will not be available", CARD_FILENAME)
        return True

    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL_BASE, str(frontend_dir), cache_headers=False)]
    )
    if "frontend" in hass.config.components:
        add_extra_js_url(hass, f"{CARD_URL_BASE}/{CARD_FILENAME}?v={VERSION}")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: GitSyncConfigEntry) -> bool:
    """Set up a repository from a config entry."""
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
            async_track_time_interval(
                hass, _auto_commit, timedelta(minutes=interval), name=f"{DOMAIN} auto commit"
            )
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
