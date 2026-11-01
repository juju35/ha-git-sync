"""Fixtures for Git Sync tests: a work tree pushing to a local bare remote."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

import pytest
from homeassistant.helpers import frame

from custom_components.git_sync.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components/ in every test."""
    yield


class _DeprecationRecorder(logging.Handler):
    """Collects Home Assistant deprecation reports that name this integration."""

    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        lowered = message.lower()
        reported = record.name == frame.__name__ or "deprecated" in lowered or "will stop working" in lowered
        if reported and (f"'{DOMAIN}'" in message or f"custom_components/{DOMAIN}/" in message):
            self.messages.append(message)


@pytest.fixture(autouse=True)
def no_deprecated_calls():
    """Fail a test whose code path makes Home Assistant report a deprecated call of this integration.

    Silent on Home Assistant versions without the deprecation; on newer ones, catches what is left.
    Messages also go to $DEPRECATIONS_LOG (if set), which CI turns into annotations.
    """
    # The frame helper reports each call site once per process: forget them so every test sees its own.
    getattr(frame, "_REPORTED_INTEGRATIONS", set()).clear()
    recorder = _DeprecationRecorder()
    root = logging.getLogger()
    root.addHandler(recorder)
    try:
        yield
    finally:
        root.removeHandler(recorder)
    if recorder.messages and (path := os.environ.get("DEPRECATIONS_LOG")):
        with open(path, "a", encoding="utf-8") as log:
            log.writelines(f"{m}\n" for m in recorder.messages)
    assert not recorder.messages, "\n".join(recorder.messages)


def git(cwd: Path, *args: str) -> str:
    """Run git synchronously in tests."""
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repository with one commit, tracking a bare remote."""
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True)
    git(work, "config", "user.name", "Test")
    git(work, "config", "user.email", "test@example.com")
    (work / "configuration.yaml").write_text("default_config:\n", encoding="utf-8")
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "chore: initial")
    git(work, "remote", "add", "origin", str(remote))
    git(work, "push", "-q", "-u", "origin", "main")
    return work


@pytest.fixture
def fresh_repo(tmp_path: Path) -> Path:
    """A repository set up as the README says: one commit and a remote, never pushed (no upstream)."""
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True)
    git(work, "config", "user.name", "Test")
    git(work, "config", "user.email", "test@example.com")
    (work / "configuration.yaml").write_text("default_config:\n", encoding="utf-8")
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "chore: initial")
    git(work, "remote", "add", "origin", str(remote))
    return work
