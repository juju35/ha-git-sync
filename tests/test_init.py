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
