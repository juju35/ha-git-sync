"""Export Lovelace dashboards from .storage to a plain directory."""

from __future__ import annotations

import json
import logging
from collections.abc import Collection
from dataclasses import dataclass, field
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


@dataclass(slots=True)
class ExportResult:
    """Outcome of an export.

    files: the exported file names (written or already up to date).
    managed: the files of the export folder written by the integration, to pass as `previous` to the next
    export: `files` plus the YAML kept for a dashboard that could not be read this time.
    """

    files: list[str] = field(default_factory=list)
    managed: list[str] = field(default_factory=list)


def export_dashboards(
    storage_dir: str, export_dir: str, export_format: str, previous: Collection[str] = ()
) -> ExportResult:
    """Copy every lovelace* file from storage_dir into export_dir.

    export_format:
      - json: raw copy of the .storage files (same as `cp .storage/lovelace*`)
      - yaml: dashboard config only, as readable YAML
      - both: the two side by side

    previous: the files an earlier export wrote into this folder (its `managed` list). Those that this export
    does not produce (a deleted dashboard, a format no longer exported) are removed, so they do not stay in the
    repository forever. Any other file of the folder, such as a YAML-mode dashboard of the user named
    `lovelace-energy.yaml`, is never touched.
    """
    source = Path(storage_dir)
    target = Path(export_dir)
    target.mkdir(parents=True, exist_ok=True)

    exported: list[str] = []
    # Files to keep although not written this time: the YAML of a dashboard whose file cannot be read now.
    kept: set[str] = set()
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
                if f"{file.name}.yaml" in previous:
                    kept.add(f"{file.name}.yaml")
                continue
            name = f"{file.name}.yaml"
            content = yaml.safe_dump(config, allow_unicode=True, sort_keys=False, default_flow_style=False, width=120)
            written += _write_if_changed(target / name, content)
            exported.append(name)

    removed = _remove_stale(source, target, set(previous) - set(exported) - kept)
    _LOGGER.debug("Exported %d dashboard files to %s (%d changed, %d removed)", len(exported), target, written, removed)
    return ExportResult(files=exported, managed=[*exported, *sorted(kept)])


def _remove_stale(source: Path, target: Path, stale: set[str]) -> int:
    """Delete the files of an earlier export that this one no longer produces."""
    if target.resolve() == source.resolve():
        # Exporting into .storage itself: its lovelace* files are the dashboards, never delete them.
        return 0
    removed = 0
    for name in stale:
        file = target / name
        # Only plain names of this folder: a corrupted manifest must not reach another directory.
        if Path(name).name != name or not name.startswith("lovelace") or not file.is_file():
            continue
        file.unlink()
        removed += 1
    return removed
