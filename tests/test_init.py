"""Config flow, setup and services."""

from __future__ import annotations

from pathlib import Path

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.git_sync.const import (
    CONF_COMMIT_INTERVAL,
    CONF_EXPORT_DIR,
    CONF_EXPORT_ENABLED,
    CONF_REMOTE,
    CONF_REPO_PATH,
    CONF_SSH_KEY,
    DOMAIN,
)

from .conftest import git


async def test_config_flow(hass: HomeAssistant, repo: Path, tmp_path: Path) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM

    bad = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_REPO_PATH: str(tmp_path), CONF_REMOTE: "origin", CONF_SSH_KEY: ""},
    )
    assert bad["errors"] == {CONF_REPO_PATH: "not_a_repository"}

    done = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_REPO_PATH: str(repo), CONF_REMOTE: "origin", CONF_SSH_KEY: ""},
    )
    assert done["type"] is FlowResultType.CREATE_ENTRY
    assert done["data"][CONF_REPO_PATH] == str(repo)


async def test_setup_and_commit(hass: HomeAssistant, repo: Path, tmp_path: Path) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=str(repo),
        data={CONF_REPO_PATH: str(repo), CONF_REMOTE: "origin", CONF_SSH_KEY: ""},
        options={
            CONF_COMMIT_INTERVAL: 0,
            CONF_EXPORT_ENABLED: False,
            CONF_EXPORT_DIR: str(tmp_path / "export"),
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    states = [s for s in hass.states.async_all("sensor") if s.attributes.get("changed_count") is not None]
    assert len(states) == 1
    assert states[0].state == "clean"

    (repo / "scripts.yaml").write_text("{}\n", encoding="utf-8")
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(states[0].entity_id).state == "dirty"

    response = await hass.services.async_call(
        DOMAIN, "commit_push", {"message": "feat: add scripts"}, blocking=True, return_response=True
    )
    assert response["results"][0]["committed"] is True
    assert git(repo, "log", "-1", "--format=%s", "origin/main").strip() == "feat: add scripts"
    assert hass.states.get(states[0].entity_id).state == "clean"

    response = await hass.services.async_call(DOMAIN, "commit_push", {}, blocking=True, return_response=True)
    assert response["results"][0]["committed"] is False

    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_card_resource(hass: HomeAssistant, repo: Path, tmp_path: Path) -> None:
    from custom_components.git_sync import _storage_resources
    from custom_components.git_sync.const import CARD_URL, VERSION

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=str(repo),
        data={CONF_REPO_PATH: str(repo), CONF_REMOTE: "origin", CONF_SSH_KEY: ""},
        options={CONF_COMMIT_INTERVAL: 0, CONF_EXPORT_ENABLED: False, CONF_EXPORT_DIR: str(tmp_path / "export")},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    resources = _storage_resources(hass)
    assert resources is not None
    urls = [item["url"] for item in resources.async_items()]
    assert urls == [f"{CARD_URL}?v={VERSION}"]

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert not [item for item in resources.async_items() if item["url"].startswith(CARD_URL)]


def _mock_ai_task(hass: HomeAssistant, answer: str) -> list[dict]:
    """Register a fake ai_task.generate_data returning `answer`; return the calls made."""
    from homeassistant.core import ServiceCall, SupportsResponse

    calls: list[dict] = []

    async def generate(call: ServiceCall) -> dict:
        calls.append(dict(call.data))
        return {"conversation_id": "x", "data": answer}

    hass.services.async_register("ai_task", "generate_data", generate, supports_response=SupportsResponse.ONLY)
    return calls


async def test_generate_message(hass: HomeAssistant, repo: Path, tmp_path: Path) -> None:
    import pytest
    from homeassistant.exceptions import ServiceValidationError

    from custom_components.git_sync.const import CONF_AI_TASK_ENTITY

    calls = _mock_ai_task(hass, "`feat: add the scripts file`.\nsecond line")
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=str(repo),
        data={CONF_REPO_PATH: str(repo), CONF_REMOTE: "origin", CONF_SSH_KEY: ""},
        options={CONF_COMMIT_INTERVAL: 0, CONF_EXPORT_ENABLED: False, CONF_AI_TASK_ENTITY: "ai_task.test"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Nothing changed: no message, the AI task is not called.
    response = await hass.services.async_call(DOMAIN, "generate_message", {}, blocking=True, return_response=True)
    assert response == {"message": None}
    assert not calls

    # A file partly staged by the user keeps its index state: the preview uses a copy of the index.
    (repo / "scripts.yaml").write_text("{}\n", encoding="utf-8")
    (repo / "notes.txt").write_text("x\n", encoding="utf-8")
    git(repo, "add", "notes.txt")
    response = await hass.services.async_call(DOMAIN, "generate_message", {}, blocking=True, return_response=True)
    assert response == {"message": "feat: add the scripts file"}
    assert "scripts.yaml" in calls[0]["instructions"]
    assert calls[0]["entity_id"] == "ai_task.test"
    assert git(repo, "diff", "--cached", "--name-only").split() == ["notes.txt"]
    assert git(repo, "log", "-1", "--format=%s").strip() == "chore: initial"

    # The commit uses the AI message too.
    response = await hass.services.async_call(DOMAIN, "commit_push", {}, blocking=True, return_response=True)
    assert response["results"][0]["message"] == "feat: add the scripts file"

    status = next(s for s in hass.states.async_all("sensor") if "changed_count" in s.attributes)
    assert status.attributes["ai_task"] == "ai_task.test"

    hass.config_entries.async_update_entry(entry, options={**entry.options, CONF_AI_TASK_ENTITY: None})
    await hass.async_block_till_done()
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "generate_message", {}, blocking=True, return_response=True)


async def test_default_ai_task_and_language(hass: HomeAssistant, repo: Path) -> None:
    from custom_components.git_sync.const import CONF_AI_TASK_ENTITY, CONF_COMMIT_LANGUAGE

    hass.config.language = "fr"
    hass.states.async_set("ai_task.google_ai_task", "unknown")

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    done = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REPO_PATH: str(repo), CONF_REMOTE: "origin", CONF_SSH_KEY: ""}
    )
    assert done["type"] is FlowResultType.CREATE_ENTRY
    assert done["options"] == {CONF_AI_TASK_ENTITY: "ai_task.google_ai_task", CONF_COMMIT_LANGUAGE: "fr"}


def _suggested(schema, key: str):
    for marker in schema.schema:
        if marker == key:
            return (marker.description or {}).get("suggested_value")
    raise KeyError(key)


async def test_options_suggest_the_only_ai_task(hass: HomeAssistant, repo: Path) -> None:
    from custom_components.git_sync.const import CONF_AI_TASK_ENTITY

    hass.states.async_set("ai_task.google_ai_task", "unknown")
    # An entry created before the AI task was preselected: no option at all.
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=str(repo),
        data={CONF_REPO_PATH: str(repo), CONF_REMOTE: "origin", CONF_SSH_KEY: ""},
        options={CONF_COMMIT_INTERVAL: 0, CONF_EXPORT_ENABLED: False},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    form = await hass.config_entries.options.async_init(entry.entry_id)
    assert _suggested(form["data_schema"], CONF_AI_TASK_ENTITY) == "ai_task.google_ai_task"

    # Emptied on purpose: stored as None and no longer suggested.
    done = await hass.config_entries.options.async_configure(
        form["flow_id"], {k: v for k, v in _defaults(form["data_schema"]).items() if k != CONF_AI_TASK_ENTITY}
    )
    assert done["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_AI_TASK_ENTITY] is None
    await hass.async_block_till_done()
    form = await hass.config_entries.options.async_init(entry.entry_id)
    assert _suggested(form["data_schema"], CONF_AI_TASK_ENTITY) is None


def _defaults(schema) -> dict:
    import voluptuous as vol

    return {
        str(marker): marker.default()
        for marker in schema.schema
        if isinstance(marker, vol.Marker) and marker.default is not vol.UNDEFINED
    }


def _entry(repo: Path, **options) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=str(repo),
        data={CONF_REPO_PATH: str(repo), CONF_REMOTE: "origin", CONF_SSH_KEY: ""},
        options={CONF_COMMIT_INTERVAL: 0, CONF_EXPORT_ENABLED: False, **options},
    )


def _status(hass: HomeAssistant):
    return next(s for s in hass.states.async_all("sensor") if "changed_count" in s.attributes)


async def test_readme_setup_pushes_and_tracks(hass: HomeAssistant, fresh_repo: Path) -> None:
    """`git init` + `git remote add` (no `push -u`): the commit is pushed and the next ones are seen as pending."""
    entry = _entry(fresh_repo)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    # Never pushed: the initial commit is waiting.
    assert _status(hass).state == "ahead"

    (fresh_repo / "scripts.yaml").write_text("{}\n", encoding="utf-8")
    await entry.runtime_data.async_refresh()
    response = await hass.services.async_call(
        DOMAIN, "commit_push", {"message": "feat: add scripts"}, blocking=True, return_response=True
    )
    assert response["results"][0]["committed"] is True
    assert git(fresh_repo, "log", "-1", "--format=%s", "origin/main").strip() == "feat: add scripts"
    assert _status(hass).state == "clean"
    assert _status(hass).attributes["upstream"] == "origin/main"


async def test_nothing_new_pushes_the_pending_commit(hass: HomeAssistant, fresh_repo: Path) -> None:
    """Commit & push with only a pending push: pushed, last push updated, reported as pushed."""
    entry = _entry(fresh_repo)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    last_push = next(s for s in hass.states.async_all("sensor") if s.entity_id.endswith("_last_push"))
    assert hass.states.get(last_push.entity_id).state == "unknown"

    response = await hass.services.async_call(DOMAIN, "commit_push", {}, blocking=True, return_response=True)
    result = response["results"][0]
    assert (result["committed"], result["pushed"], result["message"]) == (False, True, None)
    assert git(fresh_repo, "log", "-1", "--format=%s", "origin/main").strip() == "chore: initial"
    assert hass.states.get(last_push.entity_id).state not in ("unknown", "unavailable")
    assert hass.states.get(last_push.entity_id).attributes["message"] == "chore: initial"
    assert _status(hass).state == "clean"

    # Clean and pushed: nothing at all.
    response = await hass.services.async_call(DOMAIN, "commit_push", {}, blocking=True, return_response=True)
    assert (response["results"][0]["committed"], response["results"][0]["pushed"]) == (False, False)


async def test_failed_push_is_retried_automatically(hass: HomeAssistant, repo: Path, tmp_path: Path) -> None:
    """After a failed push on a clean tree, the automatic commit retries it."""
    import pytest
    from homeassistant.exceptions import HomeAssistantError

    entry = _entry(repo)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = entry.runtime_data

    remote = tmp_path / "remote.git"
    remote.rename(tmp_path / "away.git")
    (repo / "scripts.yaml").write_text("{}\n", encoding="utf-8")
    with pytest.raises(HomeAssistantError):
        await coordinator.async_commit_push("feat: add scripts")
    await coordinator.async_refresh()
    assert _status(hass).state == "error"
    assert coordinator.data.git.ahead == 1
    assert coordinator.dirty

    (tmp_path / "away.git").rename(remote)
    response = await hass.services.async_call(DOMAIN, "commit_push", {}, blocking=True, return_response=True)
    assert response["results"][0]["pushed"] is True
    assert git(repo, "log", "-1", "--format=%s", "origin/main").strip() == "feat: add scripts"
    assert _status(hass).state == "clean"
    assert not coordinator.dirty


async def test_remote_credentials_not_exposed(hass: HomeAssistant, repo: Path) -> None:
    """An HTTPS remote with a token: the token is in no state attribute."""
    git(repo, "remote", "set-url", "origin", "https://user:ghp_secret@github.com/me/ha.git")
    entry = _entry(repo)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    states = [s for s in hass.states.async_all() if s.entity_id.startswith(("sensor.", "button."))]
    assert states
    for state in states:
        assert "ghp_secret" not in str(state.attributes), state.entity_id
    assert _status(hass).attributes["remote_url"] == "https://github.com/me/ha.git"


async def test_options_can_be_emptied(hass: HomeAssistant, repo: Path) -> None:
    """A text field emptied in the options (left out by the frontend) is stored empty, not restored."""
    from custom_components.git_sync.const import CONF_NOTIFY_IMAGE, CONF_NOTIFY_SERVICE

    entry = _entry(repo, **{CONF_NOTIFY_SERVICE: "notify.mobile_app_phone", CONF_NOTIFY_IMAGE: "https://x/a.png"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    form = await hass.config_entries.options.async_init(entry.entry_id)
    assert _suggested(form["data_schema"], CONF_NOTIFY_SERVICE) == "notify.mobile_app_phone"
    user_input = {
        k: v for k, v in _defaults(form["data_schema"]).items() if k not in (CONF_NOTIFY_SERVICE, CONF_NOTIFY_IMAGE)
    }
    done = await hass.config_entries.options.async_configure(form["flow_id"], user_input)
    assert done["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_NOTIFY_SERVICE] == ""
    assert entry.options[CONF_NOTIFY_IMAGE] == ""
    await hass.async_block_till_done()


async def test_reconfigure_can_empty_branch_and_author(hass: HomeAssistant, repo: Path) -> None:
    from custom_components.git_sync.const import CONF_AUTHOR_EMAIL, CONF_AUTHOR_NAME, CONF_BRANCH

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=str(repo),
        data={
            CONF_REPO_PATH: str(repo),
            CONF_REMOTE: "origin",
            CONF_SSH_KEY: "",
            CONF_BRANCH: "main",
            CONF_AUTHOR_NAME: "Home Assistant",
            CONF_AUTHOR_EMAIL: "ha@example.com",
        },
        options={CONF_COMMIT_INTERVAL: 0, CONF_EXPORT_ENABLED: False},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await entry.start_reconfigure_flow(hass)
    assert _suggested(result["data_schema"], CONF_BRANCH) == "main"
    done = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REPO_PATH: str(repo), CONF_REMOTE: "origin", CONF_SSH_KEY: ""}
    )
    assert done["type"] is FlowResultType.ABORT
    assert done["reason"] == "reconfigure_successful"
    assert (entry.data[CONF_BRANCH], entry.data[CONF_AUTHOR_NAME], entry.data[CONF_AUTHOR_EMAIL]) == ("", "", "")
    await hass.async_block_till_done()
