"""Coordinator: polls git status and runs commit/push and dashboard exports."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    AI_INSTRUCTIONS,
    COMMIT_MESSAGE_MAX,
    CONF_AI_TASK_ENTITY,
    CONF_AUTHOR_EMAIL,
    CONF_AUTHOR_NAME,
    CONF_BRANCH,
    CONF_COMMIT_LANGUAGE,
    CONF_EXPORT_BEFORE_COMMIT,
    CONF_EXPORT_DIR,
    CONF_EXPORT_ENABLED,
    CONF_EXPORT_FORMAT,
    CONF_NOTIFY_IMAGE,
    CONF_NOTIFY_SERVICE,
    CONF_REMOTE,
    CONF_REPO_PATH,
    CONF_SSH_KEY,
    CONF_STATUS_INTERVAL,
    DEFAULT_BRANCH,
    DEFAULT_COMMIT_LANGUAGE,
    DEFAULT_EXPORT_DIR,
    DEFAULT_EXPORT_FORMAT,
    DEFAULT_REMOTE,
    DEFAULT_SSH_KEY,
    DEFAULT_STATUS_INTERVAL,
    DOMAIN,
    EVENT_COMMITTED,
    EVENT_EXPORTED,
    LANGUAGE_NAMES,
    STATUS_AHEAD,
    STATUS_CLEAN,
    STATUS_DIRTY,
    STATUS_ERROR,
    STORAGE_VERSION,
)
from .export import export_dashboards
from .git import GitCommit, GitError, GitRepo, GitStatus, StagedDiff, generate_ssh_key, redact_url

_LOGGER = logging.getLogger(__name__)

_UNSAFE_CHARS = re.compile(r"[`$\"]")


@dataclass(slots=True)
class GitSyncData:
    """Snapshot exposed to the entities."""

    status: str = STATUS_CLEAN
    git: GitStatus = field(default_factory=GitStatus)
    remote_url: str | None = None
    head: GitCommit | None = None
    last_push: datetime | None = None
    last_push_message: str | None = None
    last_export: datetime | None = None
    last_export_files: list[str] = field(default_factory=list)
    last_error: str | None = None
    ai_task: str | None = None


@dataclass(slots=True, frozen=True)
class CommitResult:
    """Outcome of a commit and push: the commit message (None when nothing was committed) and whether it pushed."""

    message: str | None = None
    pushed: bool = False

    @property
    def committed(self) -> bool:
        """Return True when a commit was made."""
        return self.message is not None


def sanitize_message(raw: str) -> str:
    """Keep the first line, strip shell-unsafe characters and cap the length."""
    line = next((part.strip() for part in raw.splitlines() if part.strip()), "")
    line = _UNSAFE_CHARS.sub("", line).strip().rstrip(".")
    return line[:COMMIT_MESSAGE_MAX].rstrip()


class GitSyncCoordinator(DataUpdateCoordinator[GitSyncData]):
    """Owns the repository and every write operation on it."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Set up the coordinator from the merged entry data and options."""
        self.settings: dict[str, Any] = {**entry.data, **entry.options}
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=self.settings.get(CONF_STATUS_INTERVAL, DEFAULT_STATUS_INTERVAL)),
        )
        self.repo = GitRepo(
            self.settings[CONF_REPO_PATH],
            remote=self.settings.get(CONF_REMOTE) or DEFAULT_REMOTE,
            branch=self.settings.get(CONF_BRANCH) or DEFAULT_BRANCH,
            ssh_key=self.settings.get(CONF_SSH_KEY) or DEFAULT_SSH_KEY,
            author_name=self.settings.get(CONF_AUTHOR_NAME) or "",
            author_email=self.settings.get(CONF_AUTHOR_EMAIL) or "",
        )
        self._store = self._make_store(hass, entry)
        self._lock = asyncio.Lock()
        self._state = GitSyncData(ai_task=self.settings.get(CONF_AI_TASK_ENTITY) or None)
        # Files the integration itself wrote into the export folder: the only ones a later export may delete.
        self._export_manifest: dict[str, Any] = {}

    @staticmethod
    def _make_store(hass: HomeAssistant, entry: ConfigEntry) -> Store[dict[str, Any]]:
        return Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")

    @classmethod
    async def async_remove_store(cls, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Delete the file holding the last push/export of a removed entry."""
        await cls._make_store(hass, entry).async_remove()

    # ------------------------------------------------------------------ polling

    async def async_load(self) -> None:
        """Restore the last push/export info saved across restarts."""
        stored = await self._store.async_load() or {}
        if value := stored.get("last_push"):
            self._state.last_push = dt_util.parse_datetime(value)
        self._state.last_push_message = stored.get("last_push_message")
        if value := stored.get("last_export"):
            self._state.last_export = dt_util.parse_datetime(value)
        self._state.last_export_files = stored.get("last_export_files", [])
        manifest = stored.get("export_manifest")
        if isinstance(manifest, dict) and isinstance(manifest.get("files"), list):
            self._export_manifest = manifest

    async def _async_save(self) -> None:
        state = self._state
        await self._store.async_save(
            {
                "last_push": state.last_push.isoformat() if state.last_push else None,
                "last_push_message": state.last_push_message,
                "last_export": state.last_export.isoformat() if state.last_export else None,
                "last_export_files": state.last_export_files,
                "export_manifest": self._export_manifest,
            }
        )

    async def _async_update_data(self) -> GitSyncData:
        state = self._state
        try:
            state.git = await self.repo.status()
            state.head = await self.repo.last_commit()
            # An HTTPS remote may carry a token ("https://user:token@host/…"): never expose it in the state.
            state.remote_url = redact_url(await self.repo.remote_url())
        except (GitError, OSError) as err:
            raise UpdateFailed(str(err)) from err

        # last_error only holds commit/push failures; it is cleared by the next
        # successful push, so a failed push stays visible until it is fixed.
        # It is also cleared once nothing is left to commit or push, e.g. after a `git push` run in a terminal:
        # a failed commit leaves its files staged (dirty), a failed push leaves commits ahead (push_pending).
        # A detached HEAD cannot tell whether its commits reached the remote: its error is kept.
        git_state = state.git
        if state.last_error and not (git_state.dirty or git_state.push_pending or git_state.detached):
            state.last_error = None
        if state.git.dirty:
            state.status = STATUS_DIRTY
        elif state.last_error:
            state.status = STATUS_ERROR
        elif state.git.push_pending:
            state.status = STATUS_AHEAD
        else:
            state.status = STATUS_CLEAN
        return state

    @property
    def dirty(self) -> bool:
        """Return True when there is something to commit or push.

        A failed push on a clean tree leaves the status at error with commits still waiting: they count too,
        so that the automatic commit retries the push instead of waiting for a file to change.
        """
        data = self.data
        if data is None:
            return False
        return data.status in (STATUS_DIRTY, STATUS_AHEAD) or (data.status == STATUS_ERROR and data.git.push_pending)

    # ------------------------------------------------------------------ commit / push

    async def async_commit_push(self, message: str | None = None) -> CommitResult:
        """Stage, commit and push; or push the commits left pending by an earlier failure."""
        async with self._lock:
            if self.settings.get(CONF_EXPORT_BEFORE_COMMIT) and self.settings.get(CONF_EXPORT_ENABLED, True):
                await self._export()

            try:
                diff = await self.repo.stage_all()
                if diff is None:
                    # Nothing new: push what an earlier failure (or a never pushed branch) left pending.
                    if not (await self.repo.status()).push_pending:
                        return CommitResult()
                    await self.repo.push()
                    commit_message = None
                else:
                    commit_message = sanitize_message(message or "") or await self._ai_message(diff)
                    await self.repo.commit(commit_message)
                    await self.repo.push()
            except GitError as err:
                self._state.status = STATUS_ERROR
                self._state.last_error = str(err)
                self.async_update_listeners()
                raise HomeAssistantError(str(err)) from err

            self._state.last_error = None
            self._state.last_push = dt_util.utcnow()
            await self.async_refresh()
            head = self._state.head
            self._state.last_push_message = commit_message or (head.message if head else None)
            await self._async_save()
            self.async_update_listeners()

        if diff is None:
            return CommitResult(pushed=True)
        self.hass.bus.async_fire(
            EVENT_COMMITTED,
            {
                "entry_id": self.config_entry.entry_id,
                "message": commit_message,
                "sha": head.sha if head else None,
                "files": diff.files,
            },
        )
        await self._notify(commit_message)
        return CommitResult(message=commit_message, pushed=True)

    def _fallback_message(self, diff: StagedDiff) -> str:
        return f"chore: update configuration ({diff.files} file{'s' if diff.files > 1 else ''})"

    async def _ai_message(self, diff: StagedDiff) -> str:
        """Ask the configured AI task for a commit message, with a safe fallback."""
        try:
            return await self._async_ask_ai(diff) or self._fallback_message(diff)
        except HomeAssistantError as err:
            _LOGGER.warning("AI task failed, using fallback commit message: %s", err)
            return self._fallback_message(diff)

    async def _async_ask_ai(self, diff: StagedDiff) -> str | None:
        """Return the AI task's message, None when no AI task is set up; raise when it fails."""
        entity_id = self.settings.get(CONF_AI_TASK_ENTITY)
        if not entity_id or not self.hass.services.has_service("ai_task", "generate_data"):
            return None
        language = LANGUAGE_NAMES.get(self.settings.get(CONF_COMMIT_LANGUAGE, DEFAULT_COMMIT_LANGUAGE), "English")
        prompt = AI_INSTRUCTIONS.format(language=language, max_len=COMMIT_MESSAGE_MAX, diff=diff.as_prompt())
        response = await self.hass.services.async_call(
            "ai_task",
            "generate_data",
            {
                "task_name": "git_commit_message",
                "entity_id": entity_id,
                "instructions": prompt,
            },
            blocking=True,
            return_response=True,
        )
        data = (response or {}).get("data")
        return sanitize_message(data if isinstance(data, str) else "") or None

    @property
    def ai_task(self) -> str | None:
        """The AI task entity writing the commit messages, if any."""
        return self.settings.get(CONF_AI_TASK_ENTITY) or None

    async def async_generate_message(self) -> str | None:
        """Write a commit message for the current changes without committing. None when nothing changed."""
        if not self.ai_task:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_ai_task")
        try:
            diff = await self.repo.preview_diff()
        except GitError as err:
            raise HomeAssistantError(str(err)) from err
        if diff is None:
            return None
        message = await self._async_ask_ai(diff)
        if message is None:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="ai_task_failed")
        return message

    async def _notify(self, message: str) -> None:
        service = (self.settings.get(CONF_NOTIFY_SERVICE) or "").strip()
        if not service:
            return
        domain, _, name = service.partition(".")
        if not name:
            domain, name = "notify", domain
        payload: dict[str, Any] = {"title": "Git commit", "message": message}
        if image := self.settings.get(CONF_NOTIFY_IMAGE):
            payload["data"] = {
                "attachment": {"url": image, "content-type": image.rsplit(".", 1)[-1]},
                "image": image,
                "notification_icon": "mdi:git",
            }
        try:
            await self.hass.services.async_call(domain, name, payload, blocking=False)
        except HomeAssistantError as err:
            _LOGGER.warning("Notification via %s failed: %s", service, err)

    # ------------------------------------------------------------------ dashboards

    async def async_export_dashboards(self) -> list[str]:
        """Export dashboards (serialised with commits)."""
        async with self._lock:
            files = await self._export()
        await self.async_refresh()
        return files

    async def _export(self) -> list[str]:
        export_dir = os.path.normpath(self.settings.get(CONF_EXPORT_DIR) or DEFAULT_EXPORT_DIR)
        # Files written by an earlier export into this same folder; nothing is deleted from another folder,
        # nor on the first export after an upgrade (no manifest yet).
        manifest = self._export_manifest
        previous = manifest.get("files", []) if manifest.get("dir") == export_dir else []
        try:
            result = await self.hass.async_add_executor_job(
                export_dashboards,
                self.hass.config.path(".storage"),
                export_dir,
                self.settings.get(CONF_EXPORT_FORMAT) or DEFAULT_EXPORT_FORMAT,
                previous,
            )
        except OSError as err:
            raise HomeAssistantError(f"Dashboard export failed: {err}") from err

        files = result.files
        self._export_manifest = {"dir": export_dir, "files": result.managed}
        self._state.last_export = dt_util.utcnow()
        self._state.last_export_files = files
        await self._async_save()
        self.hass.bus.async_fire(EVENT_EXPORTED, {"entry_id": self.config_entry.entry_id, "files": files})
        return files

    # ------------------------------------------------------------------ SSH

    async def async_generate_ssh_key(self) -> str:
        """Create the deploy key if needed and return its public part."""
        try:
            return await generate_ssh_key(self.settings.get(CONF_SSH_KEY) or DEFAULT_SSH_KEY)
        except (GitError, OSError) as err:
            raise HomeAssistantError(str(err)) from err
