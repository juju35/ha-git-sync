"""Tests for the git wrapper and the dashboard export."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from custom_components.git_sync.coordinator import sanitize_message
from custom_components.git_sync.export import export_dashboards
from custom_components.git_sync.git import (
    GitError,
    GitRepo,
    GitStatus,
    _parse_branch_line,
    redact_credentials,
    redact_url,
)

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

    result = export_dashboards(str(storage), str(out), "both")
    assert result.files == ["lovelace", "lovelace.yaml"]
    assert result.managed == ["lovelace", "lovelace.yaml"]
    assert "title: Home" in (out / "lovelace.yaml").read_text(encoding="utf-8")
    assert not (out / "core.config").exists()


@pytest.mark.parametrize("branch", ["", "main"])
async def test_first_push_sets_the_upstream(fresh_repo: Path, branch: str) -> None:
    """The README setup (no `push -u`): the first push works and tracks the remote branch."""
    git_repo = GitRepo(str(fresh_repo), remote="origin", branch=branch, ssh_key="", author_name="", author_email="")
    status = await git_repo.status()
    assert status.upstream is None
    assert status.push_pending

    await git_repo.push()
    status = await git_repo.status()
    assert status.upstream == "origin/main"
    assert not status.push_pending
    assert git(fresh_repo, "log", "-1", "--format=%s", "origin/main").strip() == "chore: initial"

    # The next commit is seen as a pending push.
    (fresh_repo / "scripts.yaml").write_text("{}\n", encoding="utf-8")
    await git_repo.stage_all()
    await git_repo.commit("feat: add scripts")
    status = await git_repo.status()
    assert status.ahead == 1
    assert status.push_pending


async def test_detached_head_is_not_a_pending_push(repo: Path) -> None:
    git(repo, "checkout", "-q", "--detach")
    status = await _repo(repo).status()
    assert status.upstream is None
    assert not status.push_pending


async def test_status_does_not_rewrite_the_index(repo: Path) -> None:
    """Polling `git status` must not take index.lock, or a concurrent `git add` fails on it."""
    index = repo / ".git" / "index"
    tracked = repo / "configuration.yaml"
    before = index.stat().st_mtime_ns
    # Same content, new mtime: a plain `git status` refreshes the stat data and rewrites the index.
    os.utime(tracked, ns=(tracked.stat().st_atime_ns, tracked.stat().st_mtime_ns + 5_000_000_000))
    await _repo(repo).status()
    assert index.stat().st_mtime_ns == before
    assert _repo(repo)._env()["GIT_OPTIONAL_LOCKS"] == "0"


def test_redact_credentials() -> None:
    assert redact_url("https://user:ghp_secret@github.com/me/ha.git") == "https://github.com/me/ha.git"
    assert redact_url("https://ghp_secret@github.com/me/ha.git") == "https://github.com/me/ha.git"
    assert redact_url("git@github.com:me/ha.git") == "git@github.com:me/ha.git"
    assert redact_url("ssh://git@github.com:22/me/ha.git") == "ssh://github.com:22/me/ha.git"
    assert redact_url(None) is None
    assert (
        redact_credentials("fatal: repository 'https://u:tok@example.com/r.git/' not found")
        == "fatal: repository 'https://example.com/r.git/' not found"
    )


async def test_git_errors_hide_the_token(repo: Path) -> None:
    """A git error quoting a URL with credentials reaches last_error and the logs without them."""
    with pytest.raises(GitError) as err:
        await _repo(repo).run("checkout", "https://user:ghp_secret@github.com/me/ha.git")
    assert "github.com/me/ha.git" in str(err.value)
    assert "ghp_secret" not in str(err.value)


def _storage(tmp_path: Path, *names: str) -> Path:
    storage = tmp_path / ".storage"
    storage.mkdir(exist_ok=True)
    for name in names:
        (storage / name).write_text(
            json.dumps({"version": 1, "key": name, "data": {"config": {"views": [{"title": name}]}}}),
            encoding="utf-8",
        )
    return storage


def test_export_removes_stale_files(tmp_path: Path) -> None:
    """A deleted dashboard, or a json→yaml switch, does not leave its old file behind."""
    storage = _storage(tmp_path, "lovelace", "lovelace.old")
    out = tmp_path / "export"
    (out).mkdir()
    (out / "README.md").write_text("mine\n", encoding="utf-8")

    first = export_dashboards(str(storage), str(out), "both")
    assert first.files == [
        "lovelace",
        "lovelace.yaml",
        "lovelace.old",
        "lovelace.old.yaml",
    ]
    (storage / "lovelace.old").unlink()
    assert export_dashboards(str(storage), str(out), "yaml", first.managed).files == ["lovelace.yaml"]
    assert sorted(p.name for p in out.iterdir()) == ["README.md", "lovelace.yaml"]


def test_export_keeps_the_yaml_of_an_unreadable_dashboard(tmp_path: Path) -> None:
    storage = _storage(tmp_path, "lovelace")
    out = tmp_path / "export"
    first = export_dashboards(str(storage), str(out), "yaml")
    (storage / "lovelace").write_text("{not json", encoding="utf-8")
    second = export_dashboards(str(storage), str(out), "yaml", first.managed)
    assert second.files == []
    assert (out / "lovelace.yaml").exists()
    # Still the integration's file: removed once the dashboard is gone for good.
    assert second.managed == ["lovelace.yaml"]
    (storage / "lovelace").unlink()
    export_dashboards(str(storage), str(out), "yaml", second.managed)
    assert not (out / "lovelace.yaml").exists()


def test_export_into_the_storage_folder_deletes_nothing(tmp_path: Path) -> None:
    storage = _storage(tmp_path, "lovelace")
    first = export_dashboards(str(storage), str(storage), "yaml")
    export_dashboards(str(storage), str(storage), "json", first.managed)
    assert (storage / "lovelace").exists()
    assert (storage / "lovelace.yaml").exists()


def test_export_keeps_the_users_own_lovelace_files(tmp_path: Path) -> None:
    """Files of the export folder the integration did not write (YAML-mode dashboards) are never deleted."""
    storage = _storage(tmp_path, "lovelace")
    out = tmp_path / "export"
    out.mkdir()
    (out / "lovelace-energy.yaml").write_text("views: []\n", encoding="utf-8")
    (out / "lovelace_tablet.yaml").write_text("views: []\n", encoding="utf-8")

    export_dashboards(str(storage), str(out), "json")
    export_dashboards(str(storage), str(out), "yaml")
    assert sorted(p.name for p in out.iterdir()) == [
        "lovelace",
        "lovelace-energy.yaml",
        "lovelace.yaml",
        "lovelace_tablet.yaml",
    ]


def test_export_deletes_only_its_own_stale_files(tmp_path: Path) -> None:
    """json → yaml: the integration's old JSON goes, the user's files and names outside the folder stay."""
    storage = _storage(tmp_path, "lovelace")
    out = tmp_path / "export"
    out.mkdir()
    (out / "lovelace-energy.yaml").write_text("views: []\n", encoding="utf-8")
    (tmp_path / "lovelace.secret").write_text("x\n", encoding="utf-8")

    first = export_dashboards(str(storage), str(out), "json")
    assert first.managed == ["lovelace"]
    # A tampered manifest cannot reach outside the folder nor a file that is not a dashboard export.
    export_dashboards(str(storage), str(out), "yaml", [*first.managed, "../lovelace.secret", "README.md"])
    assert sorted(p.name for p in out.iterdir()) == ["lovelace-energy.yaml", "lovelace.yaml"]
    assert (tmp_path / "lovelace.secret").exists()


async def test_status_lists_non_ascii_names_as_is(repo: Path) -> None:
    """`git status` quotes non-ASCII paths by default ("\\303\\251t\\303\\251.yaml"): the names stay readable."""
    (repo / "été.yaml").write_text("{}\n", encoding="utf-8")
    (repo / "with space.yaml").write_text("{}\n", encoding="utf-8")
    status = await _repo(repo).status()
    assert sorted(status.files) == ["with space.yaml", "été.yaml"]


async def test_status_with_a_staged_rename(repo: Path) -> None:
    """A rename left staged (failed commit) counts once, under its new name."""
    git(repo, "mv", "configuration.yaml", "configuration é.yaml")
    status = await _repo(repo).status()
    assert status.files == ["configuration é.yaml"]
    assert status.branch == "main"
    assert status.upstream == "origin/main"
