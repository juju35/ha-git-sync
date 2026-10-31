"""Sensors for Git Sync."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import GitSyncConfigEntry
from .const import STATUSES
from .coordinator import GitSyncCoordinator, GitSyncData
from .entity import GitSyncEntity
from .git import truncate_files

PARALLEL_UPDATES = 0


def _status_attrs(data: GitSyncData) -> dict[str, Any]:
    return {
        "branch": data.git.branch,
        "upstream": data.git.upstream,
        "remote_url": data.remote_url,
        "ahead": data.git.ahead,
        "behind": data.git.behind,
        "changed_count": len(data.git.files),
        "changed_files": truncate_files(data.git.files),
        "last_error": data.last_error,
        "ai_task": data.ai_task,
    }


def _last_commit(data: GitSyncData) -> datetime | None:
    return dt_util.utc_from_timestamp(data.head.timestamp) if data.head else None


def _last_commit_attrs(data: GitSyncData) -> dict[str, Any]:
    head = data.head
    return {
        "message": head.message if head else None,
        "sha": head.sha if head else None,
        "short_sha": head.sha[:7] if head else None,
    }


@dataclass(frozen=True, kw_only=True)
class GitSyncSensorDescription(SensorEntityDescription):
    """Describe a Git Sync sensor."""

    value_fn: Callable[[GitSyncData], Any]
    attrs_fn: Callable[[GitSyncData], Mapping[str, Any]] | None = None


SENSORS: tuple[GitSyncSensorDescription, ...] = (
    GitSyncSensorDescription(
        key="status",
        device_class=SensorDeviceClass.ENUM,
        options=STATUSES,
        value_fn=lambda data: data.status,
        attrs_fn=_status_attrs,
    ),
    GitSyncSensorDescription(
        key="changed_files",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: len(data.git.files),
    ),
    GitSyncSensorDescription(
        key="last_commit",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_last_commit,
        attrs_fn=_last_commit_attrs,
    ),
    GitSyncSensorDescription(
        key="last_push",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.last_push,
        attrs_fn=lambda data: {"message": data.last_push_message},
    ),
    GitSyncSensorDescription(
        key="last_export",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.last_export,
        attrs_fn=lambda data: {"files": data.last_export_files},
    ),
    GitSyncSensorDescription(
        key="branch",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.git.branch,
        attrs_fn=lambda data: {"remote_url": data.remote_url, "upstream": data.git.upstream},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GitSyncConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the sensors."""
    coordinator = entry.runtime_data
    async_add_entities(GitSyncSensor(coordinator, description) for description in SENSORS)


class GitSyncSensor(GitSyncEntity, SensorEntity):
    """A sensor reading from the coordinator snapshot."""

    entity_description: GitSyncSensorDescription

    def __init__(self, coordinator: GitSyncCoordinator, description: GitSyncSensorDescription) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return the extra attributes."""
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)
