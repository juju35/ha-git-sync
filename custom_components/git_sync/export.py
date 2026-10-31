"""Export Lovelace dashboards from .storage to a plain directory."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml

_LOGGER = logging.getLogger(__name__)


def _write_if_changed(target: Path, content: str) -> bool:
    """Write the file only when its content differs. Return True if written."""
    if target.exists() and target.read_text(encoding="utf-8") == content:
        return False
    target.write_text(content, encoding="utf-8")
    return True


def _dashboard_config(raw: str) -> Any | None:
    """Extract the dashboard configuration from a .storage lovelace file."""
    try:
        document = json.loads(raw)
    except json.JSONDecodeError:
        return None
    data = document.get("data") if isinstance(document, dict) else None
    if isinstance(data, dict) and "config" in data:
        return data["config"]
    return data


def export_dashboards(storage_dir: str, export_dir: str, export_format: str) -> list[str]:
    """Copy every lovelace* file from storage_dir into export_dir.

    export_format:
      - json: raw copy of the .storage files (same as `cp .storage/lovelace*`)
      - yaml: dashboard config only, as readable YAML
      - both: the two side by side

    Returns the list of exported file names (written or already up to date).
    """
    source = Path(storage_dir)
    target = Path(export_dir)
    target.mkdir(parents=True, exist_ok=True)

    exported: list[str] = []
    written = 0
    for file in sorted(source.glob("lovelace*")):
        if not file.is_file():
            continue
        raw = file.read_text(encoding="utf-8")

        if export_format in ("json", "both"):
            name = file.name
            written += _write_if_changed(target / name, raw)
            exported.append(name)

        if export_format in ("yaml", "both"):
            config = _dashboard_config(raw)
            if config is None:
                continue
            name = f"{file.name}.yaml"
            content = yaml.safe_dump(
                config, allow_unicode=True, sort_keys=False, default_flow_style=False, width=120
            )
            written += _write_if_changed(target / name, content)
            exported.append(name)

    _LOGGER.debug("Exported %d dashboard files to %s (%d changed)", len(exported), target, written)
    return exported
