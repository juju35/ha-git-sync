"""Base entity for Git Sync."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_REPO_PATH, DOMAIN, NAME, VERSION
from .coordinator import GitSyncCoordinator


class GitSyncEntity(CoordinatorEntity[GitSyncCoordinator]):
    """Common device and unique id handling."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: GitSyncCoordinator, key: str) -> None:
        """Attach the entity to the repository device."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"{NAME} {coordinator.settings[CONF_REPO_PATH]}",
            manufacturer="juju35",
            model="Git repository",
            sw_version=VERSION,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://github.com/juju35/ha-git-sync",
        )
