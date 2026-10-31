# Git Sync for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/juju35/ha-git-sync/actions/workflows/validate.yml/badge.svg)](https://github.com/juju35/ha-git-sync/actions/workflows/validate.yml)
[![Lint](https://github.com/juju35/ha-git-sync/actions/workflows/lint.yml/badge.svg)](https://github.com/juju35/ha-git-sync/actions/workflows/lint.yml)
[![Release](https://img.shields.io/github/v/release/juju35/ha-git-sync)](https://github.com/juju35/ha-git-sync/releases)

Version your Home Assistant configuration with Git, without shell commands.
Git Sync watches the `/config` work tree, commits and pushes changes on a schedule with an
AI-generated [Conventional Commits](https://www.conventionalcommits.org/) message, exports your
Lovelace dashboards out of `.storage`, and ships a Lovelace card to follow and drive all of it.

It replaces the usual `shell_command` + `command_line` sensor + script + automation stack:

| Before (YAML)                                         | With Git Sync                                   |
| ----------------------------------------------------- | ----------------------------------------------- |
| `command_line` sensor running `git status` every 60 s | `sensor.*_status` (`clean` / `dirty` / `ahead` / `error`) |
| `shell_command.git_stage_diff` + `ai_task` script     | Built-in AI commit message from the staged diff |
| `shell_command.git_commit_push_ai` + hourly automation | Automatic commit interval (option)             |
| `input_button` for a manual push                      | `button.*_commit_and_push` and the card         |
| `input_text` storing the last push                    | `sensor.*_last_push` (timestamp)                |
| `shell_command.export_dashboards` + 08:00 automation  | Daily export time (option), `button.*_export_dashboards` |
| `ssh-keygen` / `cat id_ed25519.pub` shell commands    | `git_sync.generate_ssh_key` action              |

## Features

- **Status** of the work tree: changed files, branch, upstream, commits ahead/behind.
- **Commit & push** every N minutes when something changed, or on demand (button, action, card).
- **AI commit messages** through any `ai_task` entity (Google, OpenAI, Ollama…), in English,
  French, German or Spanish, with a safe fallback when no AI task is configured or it fails.
- **Notification** after each real commit, with an optional image (iOS needs an absolute HTTPS URL).
- **Dashboard export**: copies `.storage/lovelace*` to a folder as raw JSON, readable YAML, or both,
  daily at a chosen time and optionally right before each commit. Files are only rewritten when they change.
- **SSH deploy key** generation; pushes use `StrictHostKeyChecking=accept-new` with a dedicated
  `known_hosts` next to the key, so no manual `ssh-keyscan` is needed.
- **Lovelace card** bundled with the integration, no extra resource to add.
- Events `git_sync_committed` and `git_sync_exported` for your own automations.
- UI in English, French, German and Spanish.

## Requirements

- Home Assistant 2025.6 or newer, with `git` and `ssh` available (they are in the official images).
- The configuration folder is already a Git repository with a remote:

  ```bash
  cd /config
  git init -b main
  git remote add origin git@github.com:<you>/homeassistant-config.git
  ```

- A `.gitignore` that keeps secrets and runtime data out of the repository, for example:

  ```gitignore
  secrets.yaml
  .storage/
  .cloud/
  .ssh/
  *.db*
  *.log*
  home-assistant_v2.db*
  deps/
  tts/
  __pycache__/
  ```

> [!WARNING]
> Everything that is not ignored gets pushed. Keep credentials in `secrets.yaml` (`!secret`)
> and prefer a **private** repository.

## Installation

### HACS

1. HACS → ⋮ → *Custom repositories* → `https://github.com/juju35/ha-git-sync`, category *Integration*.
2. Install **Git Sync** and restart Home Assistant.

### Manual

Download `git_sync.zip` from the [latest release](https://github.com/juju35/ha-git-sync/releases/latest),
extract it into `config/custom_components/git_sync/` and restart.

## Configuration

*Settings → Devices & services → Add integration → Git Sync*

| Field          | Default                   | Description                                             |
| -------------- | ------------------------- | ------------------------------------------------------- |
| Repository path | `/config`                | Folder containing `.git`                                |
| Remote         | `origin`                  | Remote to push to                                       |
| Branch         | *(current branch)*        | Target branch on the remote                             |
| SSH private key | `/config/.ssh/id_ed25519` | Key used for the push                                   |
| Author name / email | *(repository config)* | Overrides `user.name` / `user.email`                    |

Options (*Configure* on the integration):

| Option                       | Default                     |
| ---------------------------- | --------------------------- |
| AI task entity               | none (generic message)      |
| Commit message language      | English                     |
| Automatic commit interval    | 60 min (0 disables it)      |
| Status refresh interval      | 60 s                        |
| Notification action          | none, e.g. `notify.mobile_app_phone` |
| Notification image URL       | none                        |
| Daily dashboard export       | on                          |
| Export time                  | 08:00                       |
| Export folder                | `/config/dashboards_export` |
| Export format                | JSON                        |
| Export before each commit    | off                         |

### SSH deploy key

1. *Developer tools → Actions* → `git_sync.generate_ssh_key` → *Perform action*: the response
   contains the public key (an existing key is reused).
2. GitHub → repository → *Settings → Deploy keys → Add deploy key*, paste it and tick
   **Allow write access**.

## Entities

| Entity                     | Description                                                       |
| -------------------------- | ----------------------------------------------------------------- |
| `sensor.*_status`          | `clean`, `dirty`, `ahead` or `error`; attributes: branch, remote, changed files, last error |
| `sensor.*_changed_files`   | Number of changed files                                           |
| `sensor.*_last_commit`     | HEAD commit time; attributes: message, sha                        |
| `sensor.*_last_push`       | Last successful push by Git Sync; attribute: message              |
| `sensor.*_last_export`     | Last dashboard export; attribute: files                           |
| `sensor.*_branch`          | Current branch (diagnostic)                                       |
| `button.*_commit_and_push` | Commit and push now                                               |
| `button.*_export_dashboards` | Export the dashboards now                                       |

## Actions

```yaml
# Commit and push, AI message when "message" is omitted
action: git_sync.commit_push
data:
  message: "fix(corridor): lower the night light threshold"   # optional
response_variable: result   # {"results": [{"committed": true, "message": "..."}]}

# Export the dashboards now
action: git_sync.export_dashboards

# Create the deploy key (or read the existing one)
action: git_sync.generate_ssh_key
response_variable: key      # {"public_key": "ssh-ed25519 AAAA... homeassistant"}
```

Every action accepts an optional `config_entry_id` when several repositories are configured.

### Events

```yaml
triggers:
  - trigger: event
    event_type: git_sync_committed   # data: message, sha, files, entry_id
```

## Card

The card is served by the integration and registered automatically.

```yaml
type: custom:git-sync-card
entity: sensor.git_sync_config_status   # optional, the first Git Sync repository is used otherwise
title: Configuration                    # optional
show_files: true                        # collapsible list of changed files
show_export: true                       # last export row and export button
```

It shows the status, the last commit, the changed files (collapsible), the last push and export,
and two actions. *Commit & push* opens a confirmation at the top of the card where a message can
be typed; left empty, the AI task writes it. A visual editor is available.

## Migrating from shell commands

Once Git Sync is configured and has pushed at least once, remove from your YAML:

- `shell_command`: `git_commit_push`, `git_status_check`, `git_stage_diff`, `git_commit_push_ai`,
  `export_dashboards`, `git_generate_ssh_key`, `git_show_ssh_key`, `add_github_known_host`
- the `command_line` *Git status* sensor
- the `git_commit_push_ia` script and the *Git autocommit & push* / *Export dashboards* automations
- `input_button.git_push_manuel`, `input_text.git_dernier_push`, `input_text.dernier_export_dashboard`
- `/config/git_push.sh`

Point Git Sync to the same key (`/config/.ssh/id_ed25519`) and the same export folder to keep
the existing deploy key and history.

## Development

```bash
npm ci
npm run build        # bundles src/ into custom_components/git_sync/frontend/
npm run lint         # Biome
pip install -r requirements_test.txt ruff vulture
ruff check . && ruff format --check .
vulture
pytest
pre-commit install
```

The card bundle is not committed: CI builds it and the release workflow ships it inside `git_sync.zip`.

## License

[MIT](LICENSE)
