"""Thin async wrapper around the git command line."""

from __future__ import annotations

import asyncio
import logging
import os
import shlex
from dataclasses import dataclass, field
from pathlib import Path

from .const import CHANGED_FILES_MAX, DIFF_MAX_CHARS, GIT_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class GitError(Exception):
    """Raised when a git command fails."""


@dataclass(slots=True)
class GitStatus:
    """Parsed result of `git status --porcelain=v1 --branch`."""

    branch: str | None = None
    upstream: str | None = None
    ahead: int = 0
    behind: int = 0
    files: list[str] = field(default_factory=list)

    @property
    def dirty(self) -> bool:
        """Return True when the working tree has changes."""
        return bool(self.files)


@dataclass(slots=True)
class GitCommit:
    """A commit as reported by `git log`."""

    sha: str
    message: str
    timestamp: int


@dataclass(slots=True)
class StagedDiff:
    """Staged changes: per-file stats and a truncated patch."""

    stat: str
    patch: str
    files: int

    def as_prompt(self) -> str:
        """Return the diff in the format sent to the AI task."""
        return f"{self.stat}\n===DIFF===\n{self.patch}"


class GitRepo:
    """Run git commands against one working tree."""

    def __init__(
        self,
        path: str,
        *,
        remote: str,
        branch: str,
        ssh_key: str,
        author_name: str,
        author_email: str,
    ) -> None:
        """Store the repository settings."""
        self.path = path
        self.remote = remote
        self.branch = branch
        self.ssh_key = ssh_key
        self.author_name = author_name
        self.author_email = author_email

    # ------------------------------------------------------------------ helpers

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["LC_ALL"] = "C"
        if self.ssh_key:
            key = Path(self.ssh_key)
            known_hosts = key.parent / "known_hosts"
            env["GIT_SSH_COMMAND"] = (
                f"ssh -i {shlex.quote(str(key))} -o IdentitiesOnly=yes "
                f"-o StrictHostKeyChecking=accept-new "
                f"-o UserKnownHostsFile={shlex.quote(str(known_hosts))}"
            )
        return env

    def _base_args(self) -> list[str]:
        args = ["git", "-C", self.path, "-c", f"safe.directory={self.path}"]
        if self.author_name:
            args += ["-c", f"user.name={self.author_name}"]
        if self.author_email:
            args += ["-c", f"user.email={self.author_email}"]
        return args

    async def run(self, *args: str, check: bool = True) -> tuple[int, str]:
        """Run a git sub-command and return (returncode, stdout)."""
        cmd = [*self._base_args(), *args]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self._env(),
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), GIT_TIMEOUT)
        except TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise GitError(f"git {args[0]} timed out after {GIT_TIMEOUT}s") from exc

        stdout = out.decode(errors="replace")
        if check and proc.returncode != 0:
            message = err.decode(errors="replace").strip() or stdout.strip()
            raise GitError(f"git {args[0]} failed: {message}")
        return proc.returncode or 0, stdout

    # ------------------------------------------------------------------ queries

    async def is_repository(self) -> bool:
        """Return True when the path is inside a git work tree."""
        try:
            code, out = await self.run("rev-parse", "--is-inside-work-tree", check=False)
        except (OSError, GitError):
            return False
        return code == 0 and out.strip() == "true"

    async def remote_url(self) -> str | None:
        """Return the URL of the configured remote."""
        code, out = await self.run("remote", "get-url", self.remote, check=False)
        return out.strip() if code == 0 else None

    async def status(self) -> GitStatus:
        """Return branch, upstream divergence and changed files."""
        _, out = await self.run("status", "--porcelain=v1", "--branch", "--untracked-files=all")
        status = GitStatus()
        for line in out.splitlines():
            if line.startswith("## "):
                _parse_branch_line(line[3:], status)
            elif line.strip():
                status.files.append(line[3:].strip().strip('"'))
        return status

    async def last_commit(self) -> GitCommit | None:
        """Return the HEAD commit, or None on an empty repository."""
        code, out = await self.run("log", "-1", "--format=%H%x1f%s%x1f%ct", check=False)
        if code != 0 or not out.strip():
            return None
        sha, message, timestamp = out.strip().split("\x1f", 2)
        return GitCommit(sha=sha, message=message, timestamp=int(timestamp))

    # ------------------------------------------------------------------ actions

    async def stage_all(self) -> StagedDiff | None:
        """Stage every change and return the staged diff, None if nothing staged."""
        await self.run("add", "-A")
        code, _ = await self.run("diff", "--cached", "--quiet", check=False)
        if code == 0:
            return None
        _, stat = await self.run("diff", "--cached", "--stat")
        _, names = await self.run("diff", "--cached", "--name-only")
        _, patch = await self.run("diff", "--cached")
        return StagedDiff(
            stat=stat.strip(),
            patch=patch[:DIFF_MAX_CHARS],
            files=len([n for n in names.splitlines() if n.strip()]),
        )

    async def commit(self, message: str) -> None:
        """Commit the staged changes."""
        await self.run("commit", "--quiet", "-m", message)

    async def push(self) -> None:
        """Push the current branch to the configured remote."""
        args = ["push", "--quiet", self.remote]
        if self.branch:
            args.append(f"HEAD:{self.branch}")
        await self.run(*args)


def _parse_branch_line(line: str, status: GitStatus) -> None:
    """Parse the `## branch...upstream [ahead N, behind M]` header."""
    head, _, tracking = line.partition(" [")
    if head.startswith("No commits yet on "):
        status.branch = head.removeprefix("No commits yet on ")
        return
    branch, _, upstream = head.partition("...")
    status.branch = branch or None
    status.upstream = upstream or None
    for part in tracking.rstrip("]").split(","):
        key, _, value = part.strip().partition(" ")
        if key == "ahead" and value.isdigit():
            status.ahead = int(value)
        elif key == "behind" and value.isdigit():
            status.behind = int(value)


def truncate_files(files: list[str]) -> list[str]:
    """Limit the changed file list exposed as an attribute."""
    return files[:CHANGED_FILES_MAX]


async def generate_ssh_key(key_path: str) -> str:
    """Create an ed25519 key pair if missing and return the public key."""
    key = Path(key_path)
    pub = key.with_name(key.name + ".pub")
    if not await asyncio.to_thread(key.exists):
        await asyncio.to_thread(key.parent.mkdir, mode=0o700, parents=True, exist_ok=True)
        proc = await asyncio.create_subprocess_exec(
            "ssh-keygen",
            "-t",
            "ed25519",
            "-C",
            "homeassistant",
            "-f",
            str(key),
            "-N",
            "",
            "-q",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, err = await proc.communicate()
        if proc.returncode != 0:
            raise GitError(f"ssh-keygen failed: {err.decode(errors='replace').strip()}")
        _LOGGER.info("Generated SSH key %s", key)
    content = await asyncio.to_thread(pub.read_text, encoding="utf-8")
    return content.strip()
