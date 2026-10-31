import { strings } from "./i18n.js";

const SCHEMA = [
  { name: "entity", selector: { entity: { integration: "git_sync", domain: "sensor" } } },
  { name: "title", selector: { text: {} } },
  {
    type: "grid",
    name: "",
    schema: [
      { name: "show_files", selector: { boolean: {} } },
      { name: "show_export", selector: { boolean: {} } },
    ],
  },
];

class GitSyncCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { show_files: true, show_export: true, ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._form) this._form.hass = hass;
    else this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (field) => strings(this._hass).editor[field.name] ?? field.name;
      this._form.addEventListener("value-changed", (ev) => {
        this._config = ev.detail.value;
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: this._config },
            bubbles: true,
            composed: true,
          }),
        );
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = SCHEMA;
    this._form.data = this._config;
  }
}

customElements.define("git-sync-card-editor", GitSyncCardEditor);
