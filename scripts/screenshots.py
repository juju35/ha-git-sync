"""Render the Git Sync card with mock data and save the README screenshots.

Usage: python scripts/screenshots.py  (needs `pip install playwright` and `playwright install chromium`)
CHROMIUM_PATH=/path/to/chrome to use another browser. The clock is frozen so the "x min ago" stay the same.
Mock data only: no real repository, file name or person. Every capture keeps a 16 px frame of the theme background.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
CARD_JS = (ROOT / "custom_components/git_sync/frontend/git-sync-card.js").read_text()
NOW = datetime.fromisoformat("2026-10-31T14:00:00+01:00")
WIDTH = 460

THEMES = {
    "light": {
        "--primary-background-color": "#e8eaed",
        "--secondary-background-color": "#ececec",
        "--card-background-color": "#ffffff",
        "--primary-text-color": "#212121",
        "--secondary-text-color": "#727272",
        "--divider-color": "rgba(0,0,0,.12)",
    },
    "dark": {
        "--primary-background-color": "#111111",
        "--secondary-background-color": "#282828",
        "--card-background-color": "#1c1c1c",
        "--primary-text-color": "#e1e1e1",
        "--secondary-text-color": "#9b9b9b",
        "--divider-color": "rgba(225,225,225,.12)",
    },
}
COMMON = {
    "--primary-color": "#03a9f4",
    "--success-color": "#43a047",
    "--warning-color": "#ffa600",
    "--info-color": "#039be5",
    "--error-color": "#db4437",
    "--text-primary-color": "#ffffff",
}

# Material Design Icons paths used by the card (from @mdi/js).
ICONS = {
    "git": "M2.6,10.59L8.38,4.8L10.07,6.5C9.83,7.35 10.22,8.28 11,8.73V14.27C10.4,14.61 10,15.26 10,16A2,2 0 0,0 12,18A2,2 0 0,0 14,16C14,15.26 13.6,14.61 13,14.27V9.41L15.07,11.5C15,11.65 15,11.82 15,12A2,2 0 0,0 17,14A2,2 0 0,0 19,12A2,2 0 0,0 17,10C16.82,10 16.65,10 16.5,10.07L13.93,7.5C14.19,6.57 13.71,5.55 12.78,5.16C12.35,5 11.9,4.96 11.5,5.07L9.8,3.38L10.59,2.6C11.37,1.81 12.63,1.81 13.41,2.6L21.4,10.59C22.19,11.37 22.19,12.63 21.4,13.41L13.41,21.4C12.63,22.19 11.37,22.19 10.59,21.4L2.6,13.41C1.81,12.63 1.81,11.37 2.6,10.59Z",
    "chevron-right": "M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",
    "file-document-multiple-outline": "M16 0H8C6.9 0 6 .9 6 2V18C6 19.1 6.9 20 8 20H20C21.1 20 22 19.1 22 18V6L16 0M20 18H8V2H15V7H20V18M4 4V22H20V24H4C2.9 24 2 23.1 2 22V4H4M10 10V12H18V10H10M10 14V16H15V14H10Z",
    "cloud-check-outline": "M13 19C13 19.34 13.04 19.67 13.09 20H6.5C5 20 3.69 19.5 2.61 18.43C1.54 17.38 1 16.09 1 14.58C1 13.28 1.39 12.12 2.17 11.1S4 9.43 5.25 9.15C5.67 7.62 6.5 6.38 7.75 5.43S10.42 4 12 4C13.95 4 15.6 4.68 16.96 6.04C18.32 7.4 19 9.05 19 11C20.15 11.13 21.1 11.63 21.86 12.5C22.37 13.07 22.7 13.71 22.86 14.42C21.82 13.54 20.5 13 19 13C18.89 13 18.79 13 18.68 13C18.62 13 18.56 13 18.5 13H17V11C17 9.62 16.5 8.44 15.54 7.46C14.56 6.5 13.38 6 12 6S9.44 6.5 8.46 7.46C7.5 8.44 7 9.62 7 11H6.5C5.53 11 4.71 11.34 4.03 12.03C3.34 12.71 3 13.53 3 14.5S3.34 16.29 4.03 17C4.71 17.66 5.53 18 6.5 18H13.09C13.04 18.33 13 18.66 13 19M17.75 19.43L16.16 17.84L15 19L17.75 22L22.5 17.25L21.34 15.84L17.75 19.43Z",
    "view-dashboard-outline": "M19,5V7H15V5H19M9,5V11H5V5H9M19,13V19H15V13H19M9,17V19H5V17H9M21,3H13V9H21V3M11,3H3V13H11V3M21,11H13V21H21V11M11,15H3V21H11V15Z",
    "source-commit-end": "M17,12A5,5 0 0,1 12,17A5,5 0 0,1 7,12C7,9.58 8.72,7.56 11,7.1V3H13V7.1C15.28,7.56 17,9.58 17,12M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9Z",
    "export": "M23,12L19,8V11H10V13H19V16M1,18V6C1,4.89 1.9,4 3,4H15A2,2 0 0,1 17,6V9H15V6H3V18H15V15H17V18A2,2 0 0,1 15,20H3A2,2 0 0,1 1,18Z",
    "close": "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",
    "loading": "M12,4V2A10,10 0 0,0 2,12H4A8,8 0 0,1 12,4Z",
}

# Minimal stand-ins for Home Assistant's <ha-card> and <ha-icon>.
HA_ELEMENTS = (
    "const ICONS = "
    + json.dumps(ICONS)
    + ";"
    + """
customElements.define("ha-card", class extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" }).innerHTML =
      "<style>:host{display:block;background:var(--card-background-color);border-radius:12px;" +
      "border:1px solid var(--divider-color);color:var(--primary-text-color);overflow:hidden}</style><slot></slot>";
  }
});
customElements.define("ha-icon", class extends HTMLElement {
  static get observedAttributes() { return ["icon"]; }
  connectedCallback() { this._draw(); }
  attributeChangedCallback() { this._draw(); }
  _draw() {
    const path = ICONS[(this.getAttribute("icon") || "").replace("mdi:", "")] || "";
    this.style.display = "inline-flex";
    this.innerHTML = '<svg viewBox="0 0 24 24" style="width:var(--mdc-icon-size,24px);height:var(--mdc-icon-size,24px);fill:currentColor"><path d="' + path + '"/></svg>';
  }
});"""
)

STATUS = "sensor.git_sync_config_status"
LAST_COMMIT = "sensor.git_sync_config_last_commit"
LAST_PUSH = "sensor.git_sync_config_last_push"
LAST_EXPORT = "sensor.git_sync_config_last_export"


def ago(**delta) -> str:
    return (NOW - timedelta(**delta)).isoformat()


FILES = [
    "automations.yaml",
    "scripts.yaml",
    "dashboards_export/lovelace.dashboard_home",
    "packages/lighting.yaml",
]


def mock_hass(status, files, error=None):
    platform = {"platform": "git_sync", "device_id": "repo"}
    return {
        "states": {
            STATUS: {
                "entity_id": STATUS,
                "state": status,
                "attributes": {
                    "branch": "main",
                    "remote_url": "git@github.com:example/homeassistant-config.git",
                    "changed_count": len(files),
                    "changed_files": files,
                    "last_error": error,
                },
            },
            LAST_COMMIT: {
                "entity_id": LAST_COMMIT,
                "state": ago(minutes=42),
                "attributes": {
                    "message": "feat(corridor): lower the night light threshold to 5 lux",
                    "short_sha": "3f9c2ab",
                },
            },
            LAST_PUSH: {"entity_id": LAST_PUSH, "state": ago(minutes=42), "attributes": {}},
            LAST_EXPORT: {
                "entity_id": LAST_EXPORT,
                "state": ago(hours=6),
                "attributes": {"files": ["lovelace", "lovelace.dashboard_home", "lovelace_dashboards"]},
            },
        },
        "entities": {
            STATUS: {**platform, "translation_key": "status"},
            LAST_COMMIT: {**platform, "translation_key": "last_commit"},
            LAST_PUSH: {**platform, "translation_key": "last_push"},
            LAST_EXPORT: {**platform, "translation_key": "last_export"},
        },
        "devices": {"repo": {"config_entries": ["entry"]}},
        "language": "en",
        "locale": {"language": "en"},
    }


DIRTY = ("dirty", FILES)
CLEAN = ("clean", [])
ERROR = ("error", [], "git push failed: Permission denied (publickey).")

# (file, theme, hass, action after mounting)
SHOTS = [
    ("card", "light", DIRTY, "files"),
    ("card-dark", "dark", DIRTY, "files"),
    ("card-clean", "light", CLEAN, None),
    ("card-clean-dark", "dark", CLEAN, None),
    ("card-error", "light", ERROR, None),
    ("card-error-dark", "dark", ERROR, None),
    ("card-confirm", "light", DIRTY, "confirm"),
    ("card-confirm-dark", "dark", DIRTY, "confirm"),
]


def page_html(theme):
    variables = "".join(f"{k}:{v};" for k, v in {**THEMES[theme], **COMMON}.items())
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
:root {{ {variables} }}
body {{ margin: 0; padding: 16px; background: var(--primary-background-color);
       font-family: Roboto, "Segoe UI", Helvetica, Arial, sans-serif; width: {WIDTH}px; }}
</style></head><body><div id="root"></div></body></html>"""


MOUNT = """([hass, dark, action]) => {
    const el = document.createElement("git-sync-card");
    el.setConfig({ type: "custom:git-sync-card" });
    el.hass = { ...hass, themes: { darkMode: dark }, callService: async () => ({}) };
    document.getElementById("root").appendChild(el);
    if (action === "files") el.shadowRoot.querySelector(".toggle").click();
    if (action === "confirm") el.shadowRoot.querySelector("#commit").click();
}"""


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        for name, theme, state, action in SHOTS:
            page = browser.new_page(device_scale_factor=2, viewport={"width": 1000, "height": 1600})
            page.on("pageerror", lambda err, name=name: print(f"{name}: page error: {err}"))
            page.clock.set_fixed_time(NOW.isoformat())
            page.set_content(page_html(theme))
            page.add_script_tag(content=HA_ELEMENTS)
            page.add_script_tag(content=CARD_JS)
            page.evaluate(MOUNT, [mock_hass(*state), theme == "dark", action])
            page.wait_for_timeout(400)
            box = page.locator("#root").bounding_box()
            clip = {"x": 0, "y": 0, "width": WIDTH + 32, "height": int(box["height"] + 0.999) + 32}
            path = ROOT / "screenshots" / f"{name}.png"
            path.parent.mkdir(exist_ok=True)
            page.screenshot(path=str(path), clip=clip, animations="disabled")
            print(path.relative_to(ROOT))
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
