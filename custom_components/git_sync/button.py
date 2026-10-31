"""Buttons for Git Sync."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GitSyncConfigEntry
from .coordinator import GitSyncCoordinator
from .entity import GitSyncEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class GitSyncButtonDescription(ButtonEntityDescription):
    """Describe a Git Sync button."""

    press_fn: Callable[[GitSyncCoordinator], Awaitable[Any]]


BUTTONS: tuple[GitSyncButtonDescription, ...] = (
    GitSyncButtonDescription(
        key="commit_push",
        press_fn=lambda coordinator: coordinator.async_commit_push(),
    ),
    GitSyncButtonDescription(
        key="export_dashboards",
        press_fn=lambda coordinator: coordinator.async_export_dashboards(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GitSyncConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the buttons."""
    coordinator = entry.runtime_data
    async_add_entities(GitSyncButton(coordinator, description) for description in BUTTONS)


class GitSyncButton(GitSyncEntity, ButtonEntity):
    """Trigger a commit/push or a dashboard export."""

    entity_description: GitSyncButtonDescription

    def __init__(self, coordinator: GitSyncCoordinator, description: GitSyncButtonDescription) -> None:
        """Initialise the button."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Run the action."""
        await self.entity_description.press_fn(self.coordinator)
