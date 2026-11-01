# Git Sync — Agent Context

## Purpose
Home Assistant custom integration that versions a configuration folder with Git: polls `git status`, commits and pushes on a schedule with an AI-written message, and exports the Lovelace dashboards out of `.storage`. It bundles a Lovelace card. It replaces a YAML stack of `shell_command`, `command_line` sensor, script and automations.

## Architecture

```
custom_components/git_sync/
├── __init__.py      # Static path + dashboard resource for the card, services, entry setup, auto-commit interval, daily export time, store removal
├── git.py           # GitRepo: async `git` subprocess wrapper (status, last commit, stage_all / preview_diff, commit, push), ssh-keygen
├── export.py        # export_dashboards(): .storage/lovelace* → export dir as json / yaml / both, written only when changed (executor)
├── coordinator.py   # GitSyncCoordinator: polling, commit/push under a lock, AI message, notify, export, Store for last push/export
├── services.py      # commit_push / export_dashboards (optional response), generate_message / generate_ssh_key (response only); config_entry_id optional
├── config_flow.py   # One entry per repo path (unique_id); reconfigure (same path); options: AI task, language, intervals, notify, export
├── sensor.py        # status (enum + attributes), changed_files, last_commit, last_push, last_export, branch (diagnostic)
├── button.py        # commit_push, export_dashboards
├── entity.py        # Service device per entry
├── frontend/git-sync-card.js   # custom:git-sync-card, finds its entities by platform + translation_key, calls the actions with returnResponse
├── const.py / icons.json / services.yaml / translations/{en,fr,de,es,it,nl,pt,pt-BR,pl,sr,sr-Latn}.json / brand/
```

## Rules
- Every git call goes through `GitRepo.run` (`-c safe.directory`, optional author, `GIT_TERMINAL_PROMPT=0`, `LC_ALL=C`, `GIT_TIMEOUT`). SSH: `-i key`, `IdentitiesOnly`, `StrictHostKeyChecking=accept-new`, `known_hosts` next to the key.
- Status: `dirty` when the work tree has changes, else `error` while `last_error` (a commit/push failure) is set, else `ahead` when commits are not pushed, else `clean`. A poll failure raises `UpdateFailed` (entities unavailable) and does not set `last_error`. `last_error` is cleared by the next successful push, including the retry of a pending push when there is nothing new to commit.
- Commit: export first if `export_before_commit`; `git add -A`; nothing staged → retry a pending push, return None. Message: the one given (sanitized), else the AI task (`ai_task.generate_data`, diff stat + `===DIFF===` + first `DIFF_MAX_CHARS` of the patch), else `chore: update configuration (n files)`. `sanitize_message` keeps the first non-empty line without backticks, `$`, `"`, final period, `COMMIT_MESSAGE_MAX` chars.
- `generate_message` (card ✨ button): `preview_diff` runs `git add -A` with `GIT_INDEX_FILE` on a temp copy of the index, so the real index is untouched; `_async_ask_ai` raises on AI failure (commits fall back to the generic message instead). Requires the AI task option (`no_ai_task`); the status sensor exposes `ai_task` so the card shows the button only then.
- Commits and exports share one lock. Timers catch exceptions so they keep running.
- Card: served at `/git_sync/git-sync-card.js`, added to the dashboard resources in storage mode or loaded with `add_extra_js_url` in YAML mode; `_storage_resources()` handles the dict (before 2025.2) and dataclass (`mode` / `resource_mode`) shapes. The resource is removed with the last entry.
- Keep Home Assistant 2024.12 compatibility (`AddEntitiesCallback`, no `async_loaded_entries`).

## Release
Bump `version` in manifest.json, `VERSION` in const.py and `GIT_SYNC_CARD_VERSION` in the card, and add its CHANGELOG.md section; pushing to main publishes `vX.Y.Z` with `git_sync.zip` when that tag doesn't exist yet. Rerun notes with the "Update release notes" workflow (input `tag`).

## Tests
`pip install -r requirements_test.txt && pytest` — real git repositories pushing to a local bare remote (`tests/conftest.py`). Card: `node --test test/*.test.mjs` (the card file is evaluated in a `vm` context with stubs). Screenshots: `python scripts/screenshots.py` (Playwright, mock data, English, 16 px frame). Job `tests` runs on Python 3.14, i.e. the latest Home Assistant; job `pytest-min-ha` runs the suite on HA 2024.12.0. An autouse fixture fails any test during which Home Assistant reports a deprecated call naming `git_sync`.
