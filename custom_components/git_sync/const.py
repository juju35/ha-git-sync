"""Constants for the Git Sync integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "git_sync"
NAME: Final = "Git Sync"
# Same as manifest.json and the card: the card URL carries it, so that browsers load a new release.
VERSION: Final = "0.1.5"

# Config entry data / options
CONF_REPO_PATH: Final = "repo_path"
CONF_BRANCH: Final = "branch"
CONF_REMOTE: Final = "remote"
CONF_SSH_KEY: Final = "ssh_key"
CONF_AUTHOR_NAME: Final = "author_name"
CONF_AUTHOR_EMAIL: Final = "author_email"
CONF_AI_TASK_ENTITY: Final = "ai_task_entity"
CONF_COMMIT_LANGUAGE: Final = "commit_language"
CONF_NOTIFY_SERVICE: Final = "notify_service"
CONF_NOTIFY_IMAGE: Final = "notify_image"
CONF_STATUS_INTERVAL: Final = "status_interval"
CONF_COMMIT_INTERVAL: Final = "commit_interval"
CONF_EXPORT_ENABLED: Final = "export_enabled"
CONF_EXPORT_TIME: Final = "export_time"
CONF_EXPORT_DIR: Final = "export_dir"
CONF_EXPORT_FORMAT: Final = "export_format"
CONF_EXPORT_BEFORE_COMMIT: Final = "export_before_commit"

DEFAULT_REPO_PATH: Final = "/config"
DEFAULT_BRANCH: Final = ""
DEFAULT_REMOTE: Final = "origin"
DEFAULT_SSH_KEY: Final = "/config/.ssh/id_ed25519"
DEFAULT_COMMIT_LANGUAGE: Final = "en"
DEFAULT_STATUS_INTERVAL: Final = 60  # seconds
DEFAULT_COMMIT_INTERVAL: Final = 60  # minutes, 0 = disabled
DEFAULT_EXPORT_TIME: Final = "08:00:00"
DEFAULT_EXPORT_DIR: Final = "/config/dashboards_export"
DEFAULT_EXPORT_FORMAT: Final = "json"

EXPORT_FORMATS: Final = ["json", "yaml", "both"]
COMMIT_LANGUAGES: Final = ["en", "fr", "de", "es"]

# Git output limits
DIFF_MAX_CHARS: Final = 8000
COMMIT_MESSAGE_MAX: Final = 100
CHANGED_FILES_MAX: Final = 50
GIT_TIMEOUT: Final = 120  # seconds

# Status values exposed by the status sensor
STATUS_CLEAN: Final = "clean"
STATUS_DIRTY: Final = "dirty"
STATUS_AHEAD: Final = "ahead"
STATUS_ERROR: Final = "error"
STATUSES: Final = [STATUS_CLEAN, STATUS_DIRTY, STATUS_AHEAD, STATUS_ERROR]

# Services
SERVICE_COMMIT_PUSH: Final = "commit_push"
SERVICE_EXPORT_DASHBOARDS: Final = "export_dashboards"
SERVICE_GENERATE_SSH_KEY: Final = "generate_ssh_key"
SERVICE_GENERATE_MESSAGE: Final = "generate_message"
ATTR_MESSAGE: Final = "message"
ATTR_CONFIG_ENTRY_ID: Final = "config_entry_id"

# Events
EVENT_COMMITTED: Final = f"{DOMAIN}_committed"
EVENT_EXPORTED: Final = f"{DOMAIN}_exported"

# The card bundled with the integration, served by Home Assistant and added to the dashboard resources.
CARD_URL: Final = f"/{DOMAIN}/git-sync-card.js"

STORAGE_VERSION: Final = 1

LANGUAGE_NAMES: Final = {
    "en": "English",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
}

AI_INSTRUCTIONS: Final = (
    "You receive the git diff of a Home Assistant configuration: first the "
    "per-file statistics, then the patch (after the ===DIFF=== line). Write ONE "
    "single-line commit message in {language}, using the Conventional Commits "
    "format (feat:, fix:, chore:, refactor:, docs:), {max_len} characters max. "
    "Be SPECIFIC: name concretely what changes (entity, automation, script, "
    "integration, dashboard, room) and the action performed, instead of a "
    'generic phrase such as "update configuration". If several files change, '
    "summarise the essentials without listing everything. Do not use quotes, "
    "backticks or dollar signs. No explanation and no final period.\n"
    "Diff:\n{diff}"
)
