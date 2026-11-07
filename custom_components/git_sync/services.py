"""Services exposed by Git Sync."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError, Unauthorized, UnknownUser
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_MESSAGE,
    DOMAIN,
    SERVICE_COMMIT_PUSH,
    SERVICE_EXPORT_DASHBOARDS,
    SERVICE_GENERATE_MESSAGE,
    SERVICE_GENERATE_SSH_KEY,
    SERVICE_GET_DIFF,
    SERVICE_PULL,
)
from .coordinator import GitSyncCoordinator

_ENTRY_SCHEMA = vol.Schema({vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string})
_COMMIT_SCHEMA = _ENTRY_SCHEMA.extend({vol.Optional(ATTR_MESSAGE): cv.string})


def _coordinators(hass: HomeAssistant, call: ServiceCall) -> list[GitSyncCoordinator]:
    """Return the targeted coordinators (one entry, or all loaded entries)."""
    entries = [e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED]
    if entry_id := call.data.get(ATTR_CONFIG_ENTRY_ID):
        entries = [entry for entry in entries if entry.entry_id == entry_id]
    if not entries:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_loaded_entry")
    return [entry.runtime_data for entry in entries]


def _admin_only(
    hass: HomeAssistant, handler: Callable[[ServiceCall], Awaitable[ServiceResponse]]
) -> Callable[[ServiceCall], Awaitable[ServiceResponse]]:
    """Refuse calls from non-admin users, like async_register_admin_service.

    That helper has no supports_response in Home Assistant 2024.12, which is still supported, so the
    same check is done here. Calls without a user (automations, scripts) are allowed.
    """

    @wraps(handler)
    async def wrapper(call: ServiceCall) -> ServiceResponse:
        if call.context.user_id:
            user = await hass.auth.async_get_user(call.context.user_id)
            if user is None:
                raise UnknownUser(context=call.context)
            if not user.is_admin:
                raise Unauthorized(context=call.context)
        return await handler(call)

    return wrapper


def async_setup_services(hass: HomeAssistant) -> None:
    """Register the integration services, for admins only (the diff can show secrets.yaml)."""

    async def commit_push(call: ServiceCall) -> ServiceResponse:
        results = []
        for coordinator in _coordinators(hass, call):
            result = await coordinator.async_commit_push(call.data.get(ATTR_MESSAGE))
            results.append(
                {
                    "config_entry_id": coordinator.config_entry.entry_id,
                    "committed": result.committed,
                    "pushed": result.pushed,
                    "message": result.message,
                }
            )
        return {"results": results}

    async def export(call: ServiceCall) -> ServiceResponse:
        results = []
        for coordinator in _coordinators(hass, call):
            files = await coordinator.async_export_dashboards()
            results.append({"config_entry_id": coordinator.config_entry.entry_id, "files": files})
        return {"results": results}

    async def pull(call: ServiceCall) -> ServiceResponse:
        results = []
        for coordinator in _coordinators(hass, call):
            pulled = await coordinator.async_pull()
            results.append({"config_entry_id": coordinator.config_entry.entry_id, "pulled": pulled})
        return {"results": results}

    async def ssh_key(call: ServiceCall) -> ServiceResponse:
        coordinator = _coordinators(hass, call)[0]
        return {"public_key": await coordinator.async_generate_ssh_key()}

    async def generate_message(call: ServiceCall) -> ServiceResponse:
        coordinator = _coordinators(hass, call)[0]
        return {"message": await coordinator.async_generate_message()}

    async def get_diff(call: ServiceCall) -> ServiceResponse:
        coordinator = _coordinators(hass, call)[0]
        return (await coordinator.async_get_diff()).as_dict()

    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE_MESSAGE,
        _admin_only(hass, generate_message),
        schema=_ENTRY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_DIFF,
        _admin_only(hass, get_diff),
        schema=_ENTRY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_COMMIT_PUSH,
        _admin_only(hass, commit_push),
        schema=_COMMIT_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_EXPORT_DASHBOARDS,
        _admin_only(hass, export),
        schema=_ENTRY_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PULL,
        _admin_only(hass, pull),
        schema=_ENTRY_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE_SSH_KEY,
        _admin_only(hass, ssh_key),
        schema=_ENTRY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
