import "./editor.js";
import { absoluteTime, relativeTime, strings } from "./i18n.js";
import { STATUS_COLORS, STYLES } from "./styles.js";

const DOMAIN = "git_sync";
const FILES_SHOWN = 30;

const escapeHtml = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
  );

/** Find the status sensor of the first Git Sync device. */
export function findStatusEntity(hass) {
  const entries = Object.values(hass?.entities || {});
  const match = entries.find(
    (e) => e.platform === DOMAIN && e.translation_key === "status" && e.entity_id.startsWith("sensor."),
  );
  return match?.entity_id;
}

/** Resolve the sibling entities of the status sensor through its device. */
function resolveEntities(hass, statusId) {
  const status = hass.entities?.[statusId];
  const result = { status: statusId };
  if (!status?.device_id) return result;
  for (const entry of Object.values(hass.entities)) {
    if (entry.device_id !== status.device_id || entry.platform !== DOMAIN) continue;
    if (entry.translation_key) result[entry.translation_key] = entry.entity_id;
  }
  const device = hass.devices?.[status.device_id];
  result.entryId = device?.config_entries?.[0];
  return result;
}

/** "git@github.com:juju35/homeassistant-config.git" -> "juju35/homeassistant-config" */
function repoName(url) {
  if (!url) return "";
  const cleaned = url.replace(/\.git$/, "");
  const match = cleaned.match(/[:/]([^/:]+\/[^/:]+)$/);
  return match ? match[1] : cleaned;
}

class GitSyncCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._filesOpen = false;
    this._confirm = false;
    this._busy = null;
    this._signature = "";
    this._onOutsideClick = this._onOutsideClick.bind(this);
  }

  static getConfigElement() {
    return document.createElement("git-sync-card-editor");
  }

  static getStubConfig(hass) {
    return { entity: findStatusEntity(hass) || "" };
  }

  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this._config = { show_files: true, show_export: true, ...config };
    this._signature = "";
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const entityId = this._config?.entity || findStatusEntity(hass);
    this._entities = entityId ? resolveEntities(hass, entityId) : null;
    const signature = this._entities
      ? Object.values(this._entities)
          .map((id) => {
            const s = hass.states[id];
            return s ? `${s.state}|${s.last_updated}` : id;
          })
          .join(";") + hass.locale?.language
      : "none";
    if (signature !== this._signature) {
      this._signature = signature;
      if (!this._confirm) this._render();
    }
  }

  connectedCallback() {
    document.addEventListener("click", this._onOutsideClick, true);
  }

  disconnectedCallback() {
    document.removeEventListener("click", this._onOutsideClick, true);
  }

  getCardSize() {
    return this._filesOpen ? 7 : 5;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, min_rows: 4 };
  }

  // ------------------------------------------------------------------ events

  _onOutsideClick(event) {
    if (!this._filesOpen || event.composedPath().includes(this)) return;
    this._filesOpen = false;
    this._render();
  }

  _toast(message) {
    this.dispatchEvent(
      new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }),
    );
  }

  async _callService(service) {
    const data = {};
    if (this._entities?.entryId) data.config_entry_id = this._entities.entryId;
    if (service === "commit_push") {
      const message = this.shadowRoot.querySelector("#message")?.value?.trim();
      if (message) data.message = message;
    }
    const t = strings(this._hass);
    this._busy = service;
    this._confirm = false;
    this._render();
    try {
      // callService(domain, service, data, target, notifyOnError, returnResponse)
      const result = await this._hass.callService(DOMAIN, service, data, undefined, false, true);
      const first = result?.response?.results?.[0];
      if (service === "commit_push") {
        this._toast(first?.committed ? t.committed(first.message) : t.nothing);
      } else {
        this._toast(t.exported(first?.files?.length ?? 0));
      }
    } catch (err) {
      this._toast(t.failed(err?.message || String(err)));
    } finally {
      this._busy = null;
      this._render();
    }
  }

  _bind() {
    const root = this.shadowRoot;
    root.querySelector(".toggle")?.addEventListener("click", () => {
      this._filesOpen = !this._filesOpen;
      this._render();
    });
    root.querySelector("#commit")?.addEventListener("click", () => {
      this._confirm = true;
      this._render();
      root.querySelector("#message")?.focus();
    });
    root.querySelector("#export")?.addEventListener("click", () => this._callService("export_dashboards"));
    root.querySelector("#cancel")?.addEventListener("click", () => {
      this._confirm = false;
      this._render();
    });
    root.querySelector(".overlay")?.addEventListener("click", () => {
      this._confirm = false;
      this._render();
    });
    root.querySelector("#confirm")?.addEventListener("click", () => this._callService("commit_push"));
    root.querySelector("#message")?.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") this._callService("commit_push");
      if (ev.key === "Escape") {
        this._confirm = false;
        this._render();
      }
    });
  }

  // ------------------------------------------------------------------ render

  _render() {
    if (!this._config) return;
    const hass = this._hass;
    const t = strings(hass);
    const ids = this._entities;
    const statusState = ids && hass?.states[ids.status];

    if (!hass) return;
    if (!statusState) {
      this.shadowRoot.innerHTML = `<style>${STYLES}</style><ha-card><div class="warning">${escapeHtml(t.not_found)}</div></ha-card>`;
      return;
    }

    const attrs = statusState.attributes;
    const status = statusState.state in STATUS_COLORS ? statusState.state : "unavailable";
    const files = attrs.changed_files || [];
    const count = attrs.changed_count ?? files.length;
    const commitState = hass.states[ids.last_commit];
    const pushState = hass.states[ids.last_push];
    const exportState = hass.states[ids.last_export];
    const valid = (s) => s && !["unknown", "unavailable"].includes(s.state);

    const subtitle = [attrs.branch, repoName(attrs.remote_url)].filter(Boolean).join(" → ");
    const busy = this._busy;

    const commitBlock = valid(commitState)
      ? `<div class="commit">
          <div class="commit-label">${escapeHtml(t.last_commit)}</div>
          <div class="commit-message">${escapeHtml(commitState.attributes.message)}</div>
          <div class="commit-meta">
            <span class="sha">${escapeHtml(commitState.attributes.short_sha)}</span>
            <span title="${escapeHtml(absoluteTime(hass, commitState.state))}">${escapeHtml(relativeTime(hass, commitState.state))}</span>
          </div>
        </div>`
      : "";

    const timeRow = (icon, label, state, extra = "") => `
      <div class="row">
        <ha-icon icon="${icon}"></ha-icon>
        <span class="label">${escapeHtml(label)}</span>
        <span class="value" title="${valid(state) ? escapeHtml(absoluteTime(hass, state.state)) : ""}">
          ${valid(state) ? escapeHtml(relativeTime(hass, state.state)) : escapeHtml(t.never)}${extra}
        </span>
      </div>`;

    const fileList =
      this._config.show_files && count > 0
        ? `<div class="row toggle" role="button" aria-expanded="${this._filesOpen}">
            <ha-icon class="chevron ${this._filesOpen ? "open" : ""}" icon="mdi:chevron-right"></ha-icon>
            <span class="label">${escapeHtml(t.changed_files)}</span>
            <span class="value">${escapeHtml(t.files(count))}</span>
          </div>
          ${
            this._filesOpen
              ? `<ul class="files">${files
                  .slice(0, FILES_SHOWN)
                  .map((f) => `<li title="${escapeHtml(f)}">${escapeHtml(f)}</li>`)
                  .join(
                    "",
                  )}${count > FILES_SHOWN ? `<li>${escapeHtml(t.more(count - FILES_SHOWN))}</li>` : ""}</ul>`
              : ""
          }`
        : `<div class="row">
            <ha-icon icon="mdi:file-document-multiple-outline"></ha-icon>
            <span class="label">${escapeHtml(t.changes)}</span>
            <span class="value">${escapeHtml(count > 0 ? t.files(count) : t.no_changes)}</span>
          </div>`;

    const exportFiles = exportState?.attributes?.files?.length;
    const exportRow = this._config.show_export
      ? timeRow(
          "mdi:view-dashboard-outline",
          t.last_export,
          exportState,
          valid(exportState) && exportFiles ? ` · ${escapeHtml(t.files(exportFiles))}` : "",
        )
      : "";

    const popup = this._confirm
      ? `<div class="overlay"></div>
        <div class="popup" role="dialog" aria-modal="true">
          <div class="popup-title">${escapeHtml(t.confirm_title)}</div>
          <div class="popup-text">${escapeHtml(t.confirm_text(count))}</div>
          <label for="message">${escapeHtml(t.message_label)}</label>
          <input id="message" type="text" maxlength="100" autocomplete="off" />
          <div class="hint">${escapeHtml(t.message_hint)}</div>
          <div class="actions">
            <button class="action" id="cancel"><ha-icon icon="mdi:close"></ha-icon>${escapeHtml(t.cancel)}</button>
            <button class="action" id="confirm"><ha-icon icon="mdi:source-commit-end"></ha-icon>${escapeHtml(t.confirm)}</button>
          </div>
        </div>`
      : "";

    const canCommit = ["dirty", "ahead", "error"].includes(status) && !busy;

    this.shadowRoot.innerHTML = `
      <style>${STYLES}</style>
      <ha-card style="--gs-status: ${STATUS_COLORS[status]}">
        <div class="header">
          <div class="badge"><ha-icon icon="mdi:git"></ha-icon></div>
          <div class="titles">
            <div class="title">${escapeHtml(this._config.title || t.title)}</div>
            <div class="subtitle">${escapeHtml(subtitle)}</div>
          </div>
          <span class="pill ${busy ? "busy" : ""}">${escapeHtml(t.status[status])}</span>
        </div>
        ${commitBlock}
        <div class="rows">
          ${fileList}
          ${timeRow("mdi:cloud-check-outline", t.last_push, pushState)}
          ${exportRow}
        </div>
        ${attrs.last_error ? `<div class="error">${escapeHtml(attrs.last_error)}</div>` : ""}
        <div class="actions">
          <button class="action ${busy === "commit_push" ? "busy" : ""}" id="commit" ${canCommit ? "" : "disabled"}>
            <ha-icon icon="${busy === "commit_push" ? "mdi:loading" : "mdi:source-commit-end"}"></ha-icon>${escapeHtml(t.commit)}
          </button>
          ${
            this._config.show_export
              ? `<button class="action ${busy === "export_dashboards" ? "busy" : ""}" id="export" ${busy ? "disabled" : ""}>
                  <ha-icon icon="${busy === "export_dashboards" ? "mdi:loading" : "mdi:export"}"></ha-icon>${escapeHtml(t.export)}
                </button>`
              : ""
          }
        </div>
        ${popup}
      </ha-card>`;
    this._bind();
  }
}

customElements.define("git-sync-card", GitSyncCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "git-sync-card",
  name: "Git Sync",
  description: "Git status, commit & push and dashboard export for the Git Sync integration.",
  preview: true,
  documentationURL: "https://github.com/juju35/ha-git-sync",
});
