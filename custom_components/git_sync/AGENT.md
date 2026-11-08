# Git Sync — Agent Context

## Purpose
Home Assistant custom integration that versions a configuration folder with Git: polls `git status`, commits and pushes on a schedule with an AI-written message, and exports the Lovelace dashboards out of `.storage`. It bundles a Lovelace card. It replaces a YAML stack of `shell_command`, `command_line` sensor, script and automations.

## Architecture

```
custom_components/git_sync/
├── __init__.py      # Static path + dashboard resource for the card, services, entry setup, auto-commit interval, daily export time, store removal
├── git.py           # GitRepo: async `git` subprocess wrapper (status, last commit, stage_all / preview_diff / preview_files / preview_changes, commit, fetch, pull_ff_only, pull_rebase, push, staged_changes, unstage_all, gitignore_missing), parse_patch, redact_secrets, is_sensitive / blocked_sensitive, append_gitignore, ssh-keygen
├── export.py        # export_dashboards(): .storage/lovelace* → export dir as json / yaml / both, written only when changed (executor)
├── coordinator.py   # GitSyncCoordinator: polling, commit/push under a lock, AI message, notify, export, Store for last push/export
├── services.py      # commit_push / export_dashboards / pull (optional response), generate_message / get_diff / generate_ssh_key (response only); config_entry_id optional; admin only (_admin_only: HA 2024.12 admin helper has no supports_response)
├── config_flow.py   # One entry per repo path (unique_id); reconfigure (same path); options: AI task, language, intervals (commit, status, fetch), pull before push, allow tracked sensitive files, notify, export
├── repairs.py       # Fix flow of the gitignore_missing issue: confirm, then append the missing lines
├── diagnostics.py   # Entry data/options + coordinator snapshot; ssh_key, author name/email redacted, remote URL userinfo stripped
├── sensor.py        # status (enum + attributes), changed_files, last_commit, last_push, last_export, branch (diagnostic)
├── button.py        # commit_push, export_dashboards
├── entity.py        # Service device per entry
├── frontend/git-sync-card.js   # custom:git-sync-card, finds its entities by platform + translation_key, calls the actions with returnResponse;
│                               # custom:git-sync-mini-card extends it (compact view, zoom button → full card, click elsewhere → back)
│                               # git-sync-diff-dialog: full-screen diff viewer appended to document.body (files left, hunks right)
├── const.py / icons.json / services.yaml / translations/{en,fr,de,es,it,nl,pt,pt-BR,pl,ro,da,sv,bg,ru,uk,hu,sk,cs,sl,lv,el,sr,sr-Latn}.json / brand/
```

## Rules
- Every git call goes through `GitRepo.run` (`-c safe.directory`, optional author, `GIT_TERMINAL_PROMPT=0`, `LC_ALL=C`, `GIT_TIMEOUT`). SSH: `-i key`, `IdentitiesOnly`, `StrictHostKeyChecking=accept-new`, `BatchMode=yes`, `known_hosts` next to the key.
- Status: `diverged` when the branch is both ahead and behind its upstream, else `dirty` when the work tree has changes, else `error` while `last_error` (a commit/push failure) is set, else `behind`, else `ahead` when commits are not pushed, else `clean`. The polling runs `git fetch` (FETCH_TIMEOUT, best effort) every `fetch_interval` minutes, not on the first refresh nor while the lock is held; it also checks `.gitignore` (repo with a configuration.yaml) and raises/clears the fixable `gitignore_missing_<entry>` issue, and clears `push_blocked_<entry>` once nothing is behind. A poll failure raises `UpdateFailed` (entities unavailable) and does not set `last_error`. `last_error` is cleared by the next successful push, including the retry of a pending push when there is nothing new to commit.
- Commit: export first if `export_before_commit`; fetch; diverged → `diverged` error + `push_blocked` issue (translation key `diverged`), behind with `pull_before_push` off → `behind_remote`; sensitive files in `preview_changes` (new ones always, tracked ones unless `allow_sensitive`, deletions allowed) → `sensitive_files`; `git add -A`, then the real index is checked again (`staged_changes`; refused → `git reset` + `sensitive_files`); after the commit, if it was behind, `pull --rebase --autostash` (conflict → `rebase --abort`, `rebase_conflict` error, issue `diverged`); push; a successful push deletes the `push_blocked` issue. nothing staged → retry a pending push, return None. Message: the one given (sanitized), else the AI task (`ai_task.generate_data`, diff stat + `===DIFF===` + first `DIFF_MAX_CHARS` of the patch), else `chore: update configuration (n files)`. `as_prompt` redacts the values of password/passwd/token/api key/secret/private_key/authorization/bearer keys and whole-word `pin` (also `- key:` list items) and any `Bearer x` (`!secret` kept). `sanitize_message` keeps the first non-empty line without backticks, `$`, `"`, final period, `COMMIT_MESSAGE_MAX` chars.
- `generate_message` (card ✨ button, refused on sensitive files like a commit) and `get_diff` (card diff viewer): `_preview_index` runs `git add -A` with `GIT_INDEX_FILE` on a temp copy of the index, so the real index is untouched. `preview_files` parses the full `git diff --cached` (`parse_patch`: one FileDiff per file, status from the header lines, hunks with both line numbers, `DIFF_FILE_MAX_LINES` lines per file and `DIFF_MAX_FILES` files, the rest counted); `_async_ask_ai` raises on AI failure (commits fall back to the generic message instead). Requires the AI task option (`no_ai_task`); the status sensor exposes `ai_task` so the card shows the button only then.
- Pull (`git_sync.pull`, card button when `behind > 0` and not dirty with commits ahead): fetch (errors raised), nothing behind → 0; not ahead → `pull --ff-only`; ahead and dirty → `diverged` error; ahead and clean → `pull_rebase` (conflict → `rebase_conflict`). Returns the commits behind.
- Auto commit (`async_auto_commit`): a `ServiceValidationError` or a blocked push (`diverged`, `behind_remote`, `rebase_conflict`) logs one warning and records (files, ahead, behind) after the attempt; skipped while it is unchanged. Any other `HomeAssistantError` is retried every interval, one warning per distinct message (`_auto_error`), no traceback.
- Card: actions (commit, pull, export, diff, ✨) only when `hass.user.is_admin`; non-admins get the status view.
- Commits and exports share one lock. Timers catch exceptions so they keep running.
- Card: served at `/git_sync/git-sync-card.js`, added to the dashboard resources in storage mode or loaded with `add_extra_js_url` in YAML mode; `_storage_resources()` handles the dict (before 2025.2) and dataclass (`mode` / `resource_mode`) shapes. The resource is removed with the last entry.
- Keep Home Assistant 2024.12 compatibility (`AddEntitiesCallback`, no `async_loaded_entries`).

## Release
Bump `version` in manifest.json, `VERSION` in const.py and `GIT_SYNC_CARD_VERSION` in the card, and add its CHANGELOG.md section; pushing to main publishes `vX.Y.Z` with `git_sync.zip` when that tag doesn't exist yet. Rerun notes with the "Update release notes" workflow (input `tag`).

## Tests
`pip install -r requirements_test.txt && pytest` — real git repositories pushing to a local bare remote (`tests/conftest.py`). Card: `node --test test/*.test.mjs` (the card file is evaluated in a `vm` context with stubs). Screenshots: `python scripts/screenshots.py` (Playwright, mock data, English, 16 px frame; card at 460 px, mini card at 300 px). Job `tests` runs on Python 3.14, i.e. the latest Home Assistant; job `pytest-min-ha` runs the suite on HA 2024.12.0. An autouse fixture fails any test during which Home Assistant reports a deprecated call naming `git_sync`.
