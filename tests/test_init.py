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
