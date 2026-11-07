"""Diagnostics: the entry settings and the last status snapshot, without credentials nor personal data."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_AUTHOR_EMAIL, CONF_AUTHOR_NAME, CONF_REMOTE, CONF_SSH_KEY
from .git import redact_credentials, redact_url

# The SSH key path, the commit author, and any secret-looking key a future option could add.
TO_REDACT = {
    CONF_SSH_KEY,
    CONF_AUTHOR_NAME,
    CONF_AUTHOR_EMAIL,
    "password",
    "token",
    "api_key",
    "secret",
    "private_key",
    "public_key",
}


def _settings(values: dict[str, Any]) -> dict[str, Any]:
    """Redact the settings; a remote given as a URL keeps its host but loses its user and password."""
    redacted = async_redact_data(values, TO_REDACT)
    if isinstance(redacted.get(CONF_REMOTE), str):
        redacted[CONF_REMOTE] = redact_url(redacted[CONF_REMOTE])
    return redacted


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return the diagnostics of a config entry."""
    coordinator = entry.runtime_data
    data: dict[str, Any] | None = None
    if coordinator.data is not None:
        data = asdict(coordinator.data)
        data["remote_url"] = redact_url(data["remote_url"])
        if data["last_error"]:
            data["last_error"] = redact_credentials(data["last_error"])
    return {
        "entry": {"data": _settings(dict(entry.data)), "options": _settings(dict(entry.options))},
        "last_update_success": coordinator.last_update_success,
        "data": data,
    }
