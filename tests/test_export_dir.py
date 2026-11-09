"""The dashboard export only writes inside the configuration folder or an allowlist_external_dirs folder."""

from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
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
from custom_components.git_sync.export import export_dir_allowed


@pytest.mark.parametrize(
    ("folder", "allowed"),
    [
        ("config", True),
        ("config/dashboards_export", True),
        ("config/sub/dir", True),
        ("shared/backups", True),
        ("config/.storage", False),
        ("config/dashboards/.hidden", False),
        ("config/../media", False),
        ("media", False),
        ("configuration", False),  # A sibling sharing the prefix is not inside the folder.
        ("link-to-media", False),  # A symlink is followed.
    ],
)
def test_export_dir_allowed(tmp_path: Path, folder: str, allowed: bool) -> None:
    (tmp_path / "media").mkdir()
    (tmp_path / "link-to-media").symlink_to(tmp_path / "media")
    assert export_dir_allowed(str(tmp_path / folder), str(tmp_path / "config"), [str(tmp_path / "shared")]) is allowed


def test_a_symlink_inside_the_config_folder_pointing_out_is_refused(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir()
    (tmp_path / "media").mkdir()
    (tmp_path / "config" / "out").symlink_to(tmp_path / "media")
    assert not export_dir_allowed(str(tmp_path / "config" / "out"), str(tmp_path / "config"), [])


def _entry(repo: Path, **options) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=str(repo),
        data={CONF_REPO_PATH: str(repo), CONF_REMOTE: "origin", CONF_SSH_KEY: ""},
        options={CONF_COMMIT_INTERVAL: 0, CONF_EXPORT_ENABLED: False, **options},
    )


async def test_options_refuse_an_export_folder_outside_the_allowed_ones(hass: HomeAssistant, repo: Path) -> None:
    import voluptuous as vol

    entry = _entry(repo)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    hass.config.allowlist_external_dirs.clear()

    form = await hass.config_entries.options.async_init(entry.entry_id)
    markers = [m for m in form["data_schema"].schema if isinstance(m, vol.Marker)]
    defaults = {str(m): m.default() for m in markers if m.default is not vol.UNDEFINED}
    assert defaults[CONF_EXPORT_DIR] == "dashboards_export"
    bad = await hass.config_entries.options.async_configure(form["flow_id"], {**defaults, CONF_EXPORT_DIR: "/media"})
    assert bad["type"] is FlowResultType.FORM
    assert bad["errors"] == {CONF_EXPORT_DIR: "export_dir_not_allowed"}

    # The default, relative, is read from the configuration folder.
    done = await hass.config_entries.options.async_configure(form["flow_id"], defaults)
    assert done["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()


async def test_export_refuses_a_folder_set_before_the_check(hass: HomeAssistant, repo: Path, tmp_path: Path) -> None:
    """An entry saved by an earlier version with a folder now refused: nothing is written there."""
    outside = tmp_path / "media"
    entry = _entry(repo, **{CONF_EXPORT_DIR: str(outside)})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    hass.config.allowlist_external_dirs.clear()

    with pytest.raises(HomeAssistantError) as err:
        await entry.runtime_data.async_export_dashboards()
    assert err.value.translation_key == "export_dir_not_allowed"
    assert not outside.exists()
    await hass.async_block_till_done()
