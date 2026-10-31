"""Fixtures: a work tree pushing to a local bare remote."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

pytest_plugins = ["pytest_homeassistant_custom_component"]


def git(cwd: Path, *args: str) -> str:
    """Run git synchronously in tests."""
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components/ in every test."""
    return


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Create a repository with one commit, tracking a bare remote."""
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
