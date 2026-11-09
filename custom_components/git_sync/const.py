"""Constants for the Git Sync integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "git_sync"
NAME: Final = "Git Sync"
# Same as manifest.json and the card: the card URL carries it, so that browsers load a new release.
VERSION: Final = "1.5.2"

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
CONF_FETCH_INTERVAL: Final = "fetch_interval"
CONF_PULL_BEFORE_PUSH: Final = "pull_before_push"
CONF_ALLOW_SENSITIVE: Final = "allow_sensitive"

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
DEFAULT_FETCH_INTERVAL: Final = 15  # minutes, 0 = only before a push
DEFAULT_PULL_BEFORE_PUSH: Final = True
DEFAULT_ALLOW_SENSITIVE: Final = False

EXPORT_FORMATS: Final = ["json", "yaml", "both"]
COMMIT_LANGUAGES: Final = [
    "en",
    "fr",
    "de",
    "es",
    "sr",
    "sr-latn",
    "it",
    "nl",
    "pt",
    "pl",
    "ro",
    "da",
    "sv",
    "bg",
    "ru",
    "uk",
    "hu",
    "sk",
    "cs",
    "sl",
    "lv",
    "el",
]

# Git output limits
DIFF_MAX_CHARS: Final = 8000
# The diff viewer of the card: lines kept per file, and files kept in one response (the rest is counted).
DIFF_FILE_MAX_LINES: Final = 2000
DIFF_MAX_FILES: Final = 200
COMMIT_MESSAGE_MAX: Final = 100
CHANGED_FILES_MAX: Final = 50
GIT_TIMEOUT: Final = 120  # seconds
# The fetch of the status polling: short, so that an unreachable remote does not hold the refresh.
FETCH_TIMEOUT: Final = 30  # seconds

# Status values exposed by the status sensor
STATUS_CLEAN: Final = "clean"
STATUS_DIRTY: Final = "dirty"
STATUS_AHEAD: Final = "ahead"
STATUS_ERROR: Final = "error"
STATUS_BEHIND: Final = "behind"
STATUS_DIVERGED: Final = "diverged"
STATUSES: Final = [STATUS_CLEAN, STATUS_DIRTY, STATUS_AHEAD, STATUS_ERROR, STATUS_BEHIND, STATUS_DIVERGED]

# Files never committed nor sent to the AI task: fnmatch patterns on the file name, or folders anywhere in the path.
SENSITIVE_NAMES: Final = (
    "secrets.yaml",
    "known_devices.yaml",
    "home-assistant_v2.db*",
    "*.pem",
    "*.key",
    "id_rsa*",
    "*.log",
)
SENSITIVE_FOLDERS: Final = (".storage", ".ssh")
# What .gitignore must exclude: (a path to test with `git check-ignore`, the line suggested when it is not).
GITIGNORE_REQUIRED: Final = (("secrets.yaml", "secrets.yaml"), (".storage/core.config", ".storage/"))

# Repairs issues, suffixed with the entry ID
ISSUE_PUSH_BLOCKED: Final = "push_blocked"
ISSUE_GITIGNORE: Final = "gitignore_missing"

# Services
SERVICE_COMMIT_PUSH: Final = "commit_push"
SERVICE_EXPORT_DASHBOARDS: Final = "export_dashboards"
SERVICE_GENERATE_SSH_KEY: Final = "generate_ssh_key"
SERVICE_GENERATE_MESSAGE: Final = "generate_message"
SERVICE_GET_DIFF: Final = "get_diff"
SERVICE_PULL: Final = "pull"
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
    "sr": "Serbian (Cyrillic script)",
    "sr-latn": "Serbian (Latin script)",
    "it": "Italian",
    "nl": "Dutch",
    "pt": "European Portuguese",
    "pl": "Polish",
    "ro": "Romanian",
    "da": "Danish",
    "sv": "Swedish",
    "bg": "Bulgarian",
    "ru": "Russian",
    "uk": "Ukrainian",
    "hu": "Hungarian",
    "sk": "Slovak",
    "cs": "Czech",
    "sl": "Slovenian",
    "lv": "Latvian",
    "el": "Greek",
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
