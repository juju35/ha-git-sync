"""Thin async wrapper around the git command line."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shlex
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .const import CHANGED_FILES_MAX, DIFF_MAX_CHARS, GIT_TIMEOUT

_LOGGER = logging.getLogger(__name__)

# "scheme://user:password@host": the userinfo of a URL, e.g. an HTTPS remote carrying a token.
_URL_USERINFO = re.compile(r"([a-zA-Z][a-zA-Z0-9+.-]*://)[^/@\s'\"]+@")


def redact_credentials(text: str) -> str:
    """Remove the user and password of every URL in a message (git errors, logs)."""
    return _URL_USERINFO.sub(r"\1", text)


def redact_url(url: str | None) -> str | None:
    """Return a remote URL without its user and password ("https://token@host/…" → "https://host/…").

    scp-like SSH remotes ("git@github.com:me/repo.git") carry no secret and are kept as they are.
    """
    if not url or "://" not in url:
        return url
    parts = urlsplit(url)
    if "@" not in parts.netloc:
        return url
    return urlunsplit(parts._replace(netloc=parts.netloc.rpartition("@")[2]))


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
    unborn: bool = False

    @property
    def dirty(self) -> bool:
        """Return True when the working tree has changes."""
        return bool(self.files)

    @property
    def detached(self) -> bool:
        """Return True when HEAD is not on a branch."""
        return self.branch is None or self.branch.startswith("HEAD ")

    @property
    def push_pending(self) -> bool:
        """Return True when commits are waiting to be pushed.

        A branch without upstream (set up with `git remote add`, never pushed with `-u`) counts as pending:
        nothing tells it is on the remote, and the push sets the upstream.
        """
        if self.ahead:
            return True
        return self.upstream is None and not self.detached and not self.unborn


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
        # The status polling runs outside the commit lock: it must not take index.lock to refresh the index,
        # or a concurrent `git add -A` fails with "Unable to create '.git/index.lock': File exists".
        env["GIT_OPTIONAL_LOCKS"] = "0"
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

    async def run(self, *args: str, check: bool = True, env: dict[str, str] | None = None) -> tuple[int, str]:
        """Run a git sub-command and return (returncode, stdout)."""
        cmd = [*self._base_args(), *args]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**self._env(), **(env or {})},
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
            raise GitError(redact_credentials(f"git {args[0]} failed: {message}"))
        return proc.returncode or 0, stdout

    # ------------------------------------------------------------------ queries

    async def is_repository(self) -> bool:
        """Return True when the path is inside a git work tree."""
        try:
            code, out = await self.run("rev-parse", "--is-inside-work-tree", check=False)
        except (OSError, GitError):
            return False
        return code == 0 and out.strip() == "true"

    async def has_identity(self) -> bool:
        """Return True when git can sign a commit here (author settings, repository, global config or host)."""
        try:
            code, _ = await self.run("var", "GIT_COMMITTER_IDENT", check=False)
        except (OSError, GitError):
            return False
        return code == 0

    async def remote_url(self) -> str | None:
        """Return the URL of the configured remote."""
        code, out = await self.run("remote", "get-url", self.remote, check=False)
        return out.strip() if code == 0 else None

    async def status(self) -> GitStatus:
        """Return branch, upstream divergence and changed files."""
        # -z: paths as they are, never quoted or escaped (non-ASCII names, spaces, quotes).
        _, out = await self.run("status", "--porcelain=v1", "-z", "--branch", "--untracked-files=all")
        status = GitStatus()
        entries = iter(out.split("\0"))
        for entry in entries:
            if entry.startswith("## "):
                _parse_branch_line(entry[3:], status)
            elif len(entry) > 3:
                status.files.append(entry[3:])
                if entry[0] in "RC":
                    # A rename or copy is followed by its original path.
                    next(entries, None)
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
        return await self._staged_diff()

    async def preview_diff(self) -> StagedDiff | None:
        """Return the diff a commit would have, without touching the real index.

        `git add -A` runs against a copy of the index (GIT_INDEX_FILE), so nothing the user staged changes.
        """
        _, index = await self.run("rev-parse", "--git-path", "index")
        index_path = Path(self.path, index.strip())
        tmp = await asyncio.to_thread(tempfile.mkdtemp, prefix="git_sync_")
        try:
            env = {"GIT_INDEX_FILE": str(Path(tmp, "index"))}
            if await asyncio.to_thread(index_path.is_file):
                await asyncio.to_thread(shutil.copyfile, index_path, env["GIT_INDEX_FILE"])
            await self.run("add", "-A", env=env)
            return await self._staged_diff(env)
        finally:
            await asyncio.to_thread(shutil.rmtree, tmp, True)

    async def _staged_diff(self, env: dict[str, str] | None = None) -> StagedDiff | None:
        code, _ = await self.run("diff", "--cached", "--quiet", check=False, env=env)
        if code == 0:
            return None
        _, stat = await self.run("diff", "--cached", "--stat", env=env)
        _, names = await self.run("diff", "--cached", "--name-only", env=env)
        _, patch = await self.run("diff", "--cached", env=env)
        return StagedDiff(
            stat=stat.strip(),
            patch=patch[:DIFF_MAX_CHARS],
            files=len([n for n in names.splitlines() if n.strip()]),
        )

    async def commit(self, message: str) -> None:
        """Commit the staged changes."""
        await self.run("commit", "--quiet", "-m", message)

    async def push(self) -> None:
        """Push the current branch to the configured remote.

        A branch without upstream (`git remote add` without `push -u`) gets one, so that the next statuses
        count the commits waiting to be pushed.
        """
        status = await self.status()
        args = ["push", "--quiet"]
        if status.upstream is None and not status.detached:
            args.append("--set-upstream")
        args.append(self.remote)
        if self.branch:
            args.append(f"HEAD:{self.branch}")
        elif status.upstream is None:
            args.append("HEAD")
        await self.run(*args)


def _parse_branch_line(line: str, status: GitStatus) -> None:
    """Parse the `## branch...upstream [ahead N, behind M]` header."""
    head, _, tracking = line.partition(" [")
    if head.startswith("No commits yet on "):
        status.branch = head.removeprefix("No commits yet on ")
        status.unborn = True
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
