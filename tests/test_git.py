"""Tests for the git wrapper and the dashboard export."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.git_sync.coordinator import sanitize_message
from custom_components.git_sync.export import export_dashboards
from custom_components.git_sync.git import GitRepo, GitStatus, _parse_branch_line

from .conftest import git


def _repo(path: Path) -> GitRepo:
    return GitRepo(str(path), remote="origin", branch="", ssh_key="", author_name="", author_email="")


def test_parse_branch_line() -> None:
    status = GitStatus()
    _parse_branch_line("main...origin/main [ahead 2, behind 1]", status)
    assert (status.branch, status.upstream, status.ahead, status.behind) == ("main", "origin/main", 2, 1)


def test_sanitize_message() -> None:
    raw = '\n  feat: add `light.salon` $automation "x".\nsecond line'
    assert sanitize_message(raw) == "feat: add light.salon automation x"
    assert len(sanitize_message("x" * 300)) == 100


async def test_status_commit_push(repo: Path) -> None:
    git_repo = _repo(repo)
    assert await git_repo.is_repository()

    status = await git_repo.status()
    assert status.branch == "main"
    assert not status.dirty

    (repo / "automations.yaml").write_text("[]\n", encoding="utf-8")
    status = await git_repo.status()
    assert status.files == ["automations.yaml"]

    diff = await git_repo.stage_all()
    assert diff is not None
    assert diff.files == 1
    assert "===DIFF===" in diff.as_prompt()

    await git_repo.commit("feat: add automations")
    await git_repo.push()
    status = await git_repo.status()
    assert not status.dirty
    assert status.ahead == 0
    assert git(repo, "log", "-1", "--format=%s", "origin/main").strip() == "feat: add automations"
    assert await git_repo.stage_all() is None


def test_export_dashboards(tmp_path: Path) -> None:
    storage = tmp_path / ".storage"
    storage.mkdir()
    (storage / "lovelace").write_text(
        json.dumps({"version": 1, "key": "lovelace", "data": {"config": {"views": [{"title": "Home"}]}}}),
        encoding="utf-8",
    )
    (storage / "core.config").write_text("{}", encoding="utf-8")
    out = tmp_path / "export"

    files = export_dashboards(str(storage), str(out), "both")
    assert files == ["lovelace", "lovelace.yaml"]
    assert "title: Home" in (out / "lovelace.yaml").read_text(encoding="utf-8")
    assert not (out / "core.config").exists()
