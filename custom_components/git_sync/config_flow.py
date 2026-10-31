"""Config and options flow for Git Sync."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import (
    COMMIT_LANGUAGES,
    CONF_AI_TASK_ENTITY,
    CONF_AUTHOR_EMAIL,
    CONF_AUTHOR_NAME,
    CONF_BRANCH,
    CONF_COMMIT_INTERVAL,
    CONF_COMMIT_LANGUAGE,
    CONF_EXPORT_BEFORE_COMMIT,
    CONF_EXPORT_DIR,
    CONF_EXPORT_ENABLED,
    CONF_EXPORT_FORMAT,
    CONF_EXPORT_TIME,
    CONF_NOTIFY_IMAGE,
    CONF_NOTIFY_SERVICE,
    CONF_REMOTE,
    CONF_REPO_PATH,
    CONF_SSH_KEY,
    CONF_STATUS_INTERVAL,
    DEFAULT_BRANCH,
    DEFAULT_COMMIT_INTERVAL,
    DEFAULT_COMMIT_LANGUAGE,
    DEFAULT_EXPORT_DIR,
    DEFAULT_EXPORT_FORMAT,
    DEFAULT_EXPORT_TIME,
    DEFAULT_REMOTE,
    DEFAULT_REPO_PATH,
    DEFAULT_SSH_KEY,
    DEFAULT_STATUS_INTERVAL,
    DOMAIN,
    EXPORT_FORMATS,
    NAME,
)
from .git import GitRepo

_TEXT = selector.TextSelector()
_EMAIL = selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.EMAIL))
_URL = selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.URL))


def _number(minimum: int, maximum: int, unit: str) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=minimum,
            max=maximum,
            step=1,
            unit_of_measurement=unit,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _choice(options: list[str], key: str) -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(options=options, translation_key=key, mode=selector.SelectSelectorMode.DROPDOWN)
    )


def _repository_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_REPO_PATH, default=defaults.get(CONF_REPO_PATH, DEFAULT_REPO_PATH)): _TEXT,
            vol.Required(CONF_REMOTE, default=defaults.get(CONF_REMOTE, DEFAULT_REMOTE)): _TEXT,
            vol.Optional(CONF_BRANCH, default=defaults.get(CONF_BRANCH, DEFAULT_BRANCH)): _TEXT,
            vol.Required(CONF_SSH_KEY, default=defaults.get(CONF_SSH_KEY, DEFAULT_SSH_KEY)): _TEXT,
            vol.Optional(CONF_AUTHOR_NAME, default=defaults.get(CONF_AUTHOR_NAME, "")): _TEXT,
            vol.Optional(CONF_AUTHOR_EMAIL, default=defaults.get(CONF_AUTHOR_EMAIL, "")): _EMAIL,
        }
    )


def _default_ai_task(hass: HomeAssistant) -> str | None:
    """The AI task entity, when there is exactly one: preselected rather than left empty."""
    entities = hass.states.async_entity_ids("ai_task")
    return entities[0] if len(entities) == 1 else None


def _default_language(hass: HomeAssistant) -> str:
    """Home Assistant's language when commit messages can be written in it, else English."""
    language = (hass.config.language or "").split("-")[0]
    return language if language in COMMIT_LANGUAGES else DEFAULT_COMMIT_LANGUAGE


def _default_options(hass: HomeAssistant) -> dict[str, Any]:
    """Options of a new entry: the only AI task and Home Assistant's language."""
    options: dict[str, Any] = {CONF_COMMIT_LANGUAGE: _default_language(hass)}
    if ai_task := _default_ai_task(hass):
        options[CONF_AI_TASK_ENTITY] = ai_task
    return options


def _options_schema(hass: HomeAssistant, options: dict[str, Any]) -> vol.Schema:
    # Never set (entries before 0.1.1): suggest the only AI task. Emptied on purpose: stored as None, stays empty.
    ai_task = options[CONF_AI_TASK_ENTITY] if CONF_AI_TASK_ENTITY in options else _default_ai_task(hass)
    return vol.Schema(
        {
            vol.Optional(
                CONF_AI_TASK_ENTITY,
                description={"suggested_value": ai_task} if ai_task else None,
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="ai_task")),
            vol.Required(
                CONF_COMMIT_LANGUAGE,
                default=options.get(CONF_COMMIT_LANGUAGE, _default_language(hass)),
            ): _choice(COMMIT_LANGUAGES, CONF_COMMIT_LANGUAGE),
            vol.Required(
                CONF_COMMIT_INTERVAL,
                default=options.get(CONF_COMMIT_INTERVAL, DEFAULT_COMMIT_INTERVAL),
            ): _number(0, 1440, "min"),
            vol.Required(
                CONF_STATUS_INTERVAL,
                default=options.get(CONF_STATUS_INTERVAL, DEFAULT_STATUS_INTERVAL),
            ): _number(10, 3600, "s"),
            vol.Optional(CONF_NOTIFY_SERVICE, default=options.get(CONF_NOTIFY_SERVICE, "")): _TEXT,
            vol.Optional(CONF_NOTIFY_IMAGE, default=options.get(CONF_NOTIFY_IMAGE, "")): _URL,
            vol.Required(
                CONF_EXPORT_ENABLED, default=options.get(CONF_EXPORT_ENABLED, True)
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_EXPORT_TIME, default=options.get(CONF_EXPORT_TIME, DEFAULT_EXPORT_TIME)
            ): selector.TimeSelector(),
            vol.Required(CONF_EXPORT_DIR, default=options.get(CONF_EXPORT_DIR, DEFAULT_EXPORT_DIR)): _TEXT,
            vol.Required(CONF_EXPORT_FORMAT, default=options.get(CONF_EXPORT_FORMAT, DEFAULT_EXPORT_FORMAT)): _choice(
                EXPORT_FORMATS, CONF_EXPORT_FORMAT
            ),
            vol.Required(
                CONF_EXPORT_BEFORE_COMMIT, default=options.get(CONF_EXPORT_BEFORE_COMMIT, False)
            ): selector.BooleanSelector(),
        }
    )


async def _validate(data: dict[str, Any]) -> dict[str, str]:
    """Check that the path is a git work tree with the given remote."""
    repo = GitRepo(
        data[CONF_REPO_PATH],
        remote=data[CONF_REMOTE],
        branch=data.get(CONF_BRANCH, ""),
        ssh_key=data[CONF_SSH_KEY],
        author_name="",
        author_email="",
    )
    if not await repo.is_repository():
        return {CONF_REPO_PATH: "not_a_repository"}
    if await repo.remote_url() is None:
        return {CONF_REMOTE: "unknown_remote"}
    return {}


class GitSyncConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a repository."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the repository settings."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_REPO_PATH] = user_input[CONF_REPO_PATH].rstrip("/") or "/"
            await self.async_set_unique_id(user_input[CONF_REPO_PATH])
            self._abort_if_unique_id_configured()
            errors = await _validate(user_input)
            if not errors:
                return self.async_create_entry(
                    title=f"{NAME} {user_input[CONF_REPO_PATH]}",
                    data=user_input,
                    options=_default_options(self.hass),
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(_repository_schema({}), user_input or {}),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Change the repository settings."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_REPO_PATH] = user_input[CONF_REPO_PATH].rstrip("/") or "/"
            errors = await _validate(user_input)
            if not errors:
                await self.async_set_unique_id(user_input[CONF_REPO_PATH])
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(entry, data_updates=user_input)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_repository_schema(user_input or dict(entry.data)),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> GitSyncOptionsFlow:
        """Return the options flow."""
        return GitSyncOptionsFlow()


class GitSyncOptionsFlow(OptionsFlow):
    """Commit message, schedules, notifications and dashboard export."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Edit the options."""
        if user_input is not None:
            for key in (CONF_COMMIT_INTERVAL, CONF_STATUS_INTERVAL):
                user_input[key] = int(user_input[key])
            # An emptied field is left out of user_input: store it as None so it isn't suggested again.
            user_input.setdefault(CONF_AI_TASK_ENTITY, None)
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init", data_schema=_options_schema(self.hass, dict(self.config_entry.options))
        )
