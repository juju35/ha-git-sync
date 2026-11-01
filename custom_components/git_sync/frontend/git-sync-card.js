/**
 * git-sync-card — the Git status of a Home Assistant configuration (changes, last commit, last push, last
 * dashboard export), with Commit & push and Export dashboards actions.
 * Served and added to the dashboard resources by the Git Sync integration.
 * https://github.com/juju35/ha-git-sync
 */
var GIT_SYNC_CARD_VERSION = '0.1.2';

const GS_I18N = {
  en: {
    title: 'Git Sync',
    clean: 'Up to date',
    dirty: 'Changes',
    ahead: 'Push pending',
    error: 'Error',
    unavailable: 'Unavailable',
    working: 'Working…',
    not_loaded: 'Git Sync is not set up',
    last_commit: 'Last commit',
    last_push: 'Last push',
    last_export: 'Dashboard export',
    changes: 'Changes',
    files_one: '{n} file',
    files_many: '{n} files',
    changed_files: 'Changed files',
    no_changes: 'Working tree clean',
    more: '+ {n} more',
    never: 'Never',
    commit: 'Commit & push',
    export: 'Export dashboards',
    confirm_title: 'Commit and push now?',
    confirm_text_one: '{n} changed file will be committed and pushed.',
    confirm_text_many: '{n} changed files will be committed and pushed.',
    confirm_push: 'The commits waiting will be pushed.',
    message: 'Message (Enter to commit on ‘{branch}’)',
    message_hint: 'Empty: written by the AI task when committing',
    generate: 'Generate commit message',
    generated_none: 'Nothing to describe: no changes',
    cancel: 'Cancel',
    committed: 'Committed: {m}',
    nothing: 'Nothing to commit',
    pushed: 'Pending commits pushed',
    exported_one: '{n} dashboard file exported',
    exported_many: '{n} dashboard files exported',
    failed: 'Failed: {e}',
    ed_entity: 'Git Sync sensor',
    ed_entity_helper: 'Status sensor of the repository; leave empty to find it automatically',
    ed_title: 'Title',
    ed_title_helper: 'Leave empty for “Git Sync”',
    ed_show_files: 'Changed files',
    ed_show_files_helper: 'Collapsible list of the files not committed yet',
    ed_show_export: 'Dashboard export',
    ed_show_export_helper: 'Time of the last export and the Export dashboards button',
    ed_language: 'Language',
    ed_language_helper: 'Leave empty to follow Home Assistant',
  },
  fr: {
    title: 'Git Sync',
    clean: 'À jour',
    dirty: 'Modifications',
    ahead: 'Push en attente',
    error: 'Erreur',
    unavailable: 'Indisponible',
    working: 'En cours…',
    not_loaded: 'Git Sync n’est pas configuré',
    last_commit: 'Dernier commit',
    last_push: 'Dernier push',
    last_export: 'Export des dashboards',
    changes: 'Modifications',
    files_one: '{n} fichier',
    files_many: '{n} fichiers',
    changed_files: 'Fichiers modifiés',
    no_changes: 'Aucune modification',
    more: '+ {n} autres',
    never: 'Jamais',
    commit: 'Commit et push',
    export: 'Exporter les dashboards',
    confirm_title: 'Commit et push maintenant ?',
    confirm_text_one: '{n} fichier modifié sera committé et poussé.',
    confirm_text_many: '{n} fichiers modifiés seront committés et poussés.',
    confirm_push: 'Les commits en attente seront poussés.',
    message: 'Message (Entrée pour committer sur « {branch} »)',
    message_hint: 'Vide : rédigé par l’AI task au moment du commit',
    generate: 'Générer le message de commit',
    generated_none: 'Rien à décrire : aucune modification',
    cancel: 'Annuler',
    committed: 'Commit : {m}',
    nothing: 'Rien à committer',
    pushed: 'Commits en attente poussés',
    exported_one: '{n} fichier de dashboard exporté',
    exported_many: '{n} fichiers de dashboard exportés',
    failed: 'Échec : {e}',
    ed_entity: 'Capteur Git Sync',
    ed_entity_helper: 'Capteur de statut du dépôt ; laisser vide pour le trouver automatiquement',
    ed_title: 'Titre',
    ed_title_helper: 'Laisser vide pour « Git Sync »',
    ed_show_files: 'Fichiers modifiés',
    ed_show_files_helper: 'Liste repliable des fichiers pas encore committés',
    ed_show_export: 'Export des dashboards',
    ed_show_export_helper: 'Heure du dernier export et bouton Exporter les dashboards',
    ed_language: 'Langue',
    ed_language_helper: 'Laisser vide pour suivre Home Assistant',
  },
  de: {
    title: 'Git Sync',
    clean: 'Aktuell',
    dirty: 'Änderungen',
    ahead: 'Push ausstehend',
    error: 'Fehler',
    unavailable: 'Nicht verfügbar',
    working: 'Läuft…',
    not_loaded: 'Git Sync ist nicht eingerichtet',
    last_commit: 'Letzter Commit',
    last_push: 'Letzter Push',
    last_export: 'Dashboard-Export',
    changes: 'Änderungen',
    files_one: '{n} Datei',
    files_many: '{n} Dateien',
    changed_files: 'Geänderte Dateien',
    no_changes: 'Keine Änderungen',
    more: '+ {n} weitere',
    never: 'Nie',
    commit: 'Commit & Push',
    export: 'Dashboards exportieren',
    confirm_title: 'Jetzt committen und pushen?',
    confirm_text_one: '{n} geänderte Datei wird committet und gepusht.',
    confirm_text_many: '{n} geänderte Dateien werden committet und gepusht.',
    confirm_push: 'Die ausstehenden Commits werden gepusht.',
    message: 'Nachricht (Eingabe zum Committen auf „{branch}“)',
    message_hint: 'Leer: beim Commit vom AI-Task geschrieben',
    generate: 'Commit-Nachricht erzeugen',
    generated_none: 'Nichts zu beschreiben: keine Änderungen',
    cancel: 'Abbrechen',
    committed: 'Committet: {m}',
    nothing: 'Nichts zu committen',
    pushed: 'Ausstehende Commits gepusht',
    exported_one: '{n} Dashboard-Datei exportiert',
    exported_many: '{n} Dashboard-Dateien exportiert',
    failed: 'Fehlgeschlagen: {e}',
    ed_entity: 'Git-Sync-Sensor',
    ed_entity_helper: 'Statussensor des Repositorys; leer lassen, um ihn automatisch zu finden',
    ed_title: 'Titel',
    ed_title_helper: 'Leer lassen für „Git Sync“',
    ed_show_files: 'Geänderte Dateien',
    ed_show_files_helper: 'Aufklappbare Liste der noch nicht committeten Dateien',
    ed_show_export: 'Dashboard-Export',
    ed_show_export_helper: 'Zeit des letzten Exports und die Schaltfläche Dashboards exportieren',
    ed_language: 'Sprache',
    ed_language_helper: 'Leer lassen, um Home Assistant zu folgen',
  },
  es: {
    title: 'Git Sync',
    clean: 'Al día',
    dirty: 'Cambios',
    ahead: 'Push pendiente',
    error: 'Error',
    unavailable: 'No disponible',
    working: 'En curso…',
    not_loaded: 'Git Sync no está configurado',
    last_commit: 'Último commit',
    last_push: 'Último push',
    last_export: 'Exportación de paneles',
    changes: 'Cambios',
    files_one: '{n} archivo',
    files_many: '{n} archivos',
    changed_files: 'Archivos modificados',
    no_changes: 'Sin cambios',
    more: '+ {n} más',
    never: 'Nunca',
    commit: 'Commit y push',
    export: 'Exportar paneles',
    confirm_title: '¿Hacer commit y push ahora?',
    confirm_text_one: 'Se hará commit y push de {n} archivo modificado.',
    confirm_text_many: 'Se hará commit y push de {n} archivos modificados.',
    confirm_push: 'Se hará push de los commits pendientes.',
    message: 'Mensaje (Intro para hacer commit en «{branch}»)',
    message_hint: 'Vacío: lo escribe la AI task al hacer commit',
    generate: 'Generar mensaje de commit',
    generated_none: 'Nada que describir: sin cambios',
    cancel: 'Cancelar',
    committed: 'Commit: {m}',
    nothing: 'Nada que confirmar',
    pushed: 'Commits pendientes enviados',
    exported_one: '{n} archivo de panel exportado',
    exported_many: '{n} archivos de panel exportados',
    failed: 'Error: {e}',
    ed_entity: 'Sensor de Git Sync',
    ed_entity_helper: 'Sensor de estado del repositorio; déjalo vacío para encontrarlo automáticamente',
    ed_title: 'Título',
    ed_title_helper: 'Déjalo vacío para «Git Sync»',
    ed_show_files: 'Archivos modificados',
    ed_show_files_helper: 'Lista plegable de los archivos aún sin commit',
    ed_show_export: 'Exportación de paneles',
    ed_show_export_helper: 'Hora de la última exportación y el botón Exportar paneles',
    ed_language: 'Idioma',
    ed_language_helper: 'Déjalo vacío para seguir a Home Assistant',
  },
};

const gsLang = (hass, config) => {
  const raw = String(config?.language || hass?.locale?.language || hass?.language || 'en');
  if (GS_I18N[raw]) return raw;
  const l = raw.slice(0, 2);
  return GS_I18N[l] ? l : 'en';
};

const gsT = (lang, key, vars = {}) =>
  (GS_I18N[lang]?.[key] ?? GS_I18N.en[key] ?? key).replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? '');

// "{n} file" / "{n} files": the *_one key for 1, *_many otherwise.
const gsN = (lang, key, n, vars = {}) => gsT(lang, `${key}_${n === 1 ? 'one' : 'many'}`, { n, ...vars });

const gsEsc = (s) =>
  String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

const GS_DEFAULTS = { show_files: true, show_export: true };
const GS_FILES_SHOWN = 30;
const GS_STATUSES = ['clean', 'dirty', 'ahead', 'error'];

// Minutes elapsed since `iso` (0 for a date in the future or unreadable).
const gsMinutes = (iso, now = Date.now()) => {
  const t = new Date(iso).getTime();
  return Number.isFinite(t) ? Math.max(0, (now - t) / 60000) : 0;
};

// The integration's entities, from the entity registry: { device: { status, last_commit, …, commit_push } }.
// Each entity is told apart by its translation key, else by the end of its entity ID (renamed IDs keep the key).
const GS_KEYS = {
  status: '_status',
  changed_files: '_changed_files',
  last_commit: '_last_commit',
  last_push: '_last_push',
  last_export: '_last_export',
  branch: '_branch',
  commit_push: '_commit_and_push',
  export_dashboards: '_export_dashboards',
};
function gsDevices(registry) {
  const devices = {};
  for (const [id, e] of Object.entries(registry || {})) {
    if (e?.platform !== 'git_sync') continue;
    const d = (devices[e.device_id || ''] ||= {});
    const keys = Object.keys(GS_KEYS);
    const key = keys.find((k) => e.translation_key === k) || keys.find((k) => id.endsWith(GS_KEYS[k]));
    if (key) d[key] = id;
  }
  return devices;
}

// "git@github.com:me/homeassistant-config.git" → "me/homeassistant-config".
const gsRepo = (url) => {
  if (!url) return '';
  const cleaned = String(url).replace(/\.git$/, '');
  const m = cleaned.match(/[:/]([^/:]+\/[^/:]+)$/);
  return m ? m[1] : cleaned;
};

class GitSyncCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement('git-sync-card-editor');
  }

  static getStubConfig() {
    return {};
  }

  constructor() {
    super();
    this._filesOpen = false;
    this._confirm = false;
    this._busy = null;
    this._draft = '';
    this._generating = false;
    this._outside = (ev) => {
      if (!this._filesOpen || ev.composedPath?.().includes(this)) return;
      this._filesOpen = false;
      this._render();
    };
  }

  connectedCallback() {
    document.addEventListener?.('click', this._outside, true);
  }

  disconnectedCallback() {
    document.removeEventListener?.('click', this._outside, true);
  }

  setConfig(config) {
    this._config = { ...GS_DEFAULTS, ...config };
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
    this._sig = null;
    this._render();
  }

  set hass(hass) {
    const old = this._hass;
    this._hass = hass;
    // Nothing the card shows changed: same state objects, registry, language and minute ("3 min ago").
    const ids = this._ids;
    if (
      old &&
      this._sig &&
      ids &&
      hass.entities === old.entities &&
      Object.values(ids).every((id) => !id || hass.states[id] === old.states[id]) &&
      gsLang(hass, this._config) === gsLang(old, this._config) &&
      Math.floor(Date.now() / 60000) === this._sigMinute
    ) {
      return;
    }
    // Typing a commit message: keep the popup as it is.
    if (this._confirm) return;
    this._render();
  }

  getCardSize() {
    return this._filesOpen ? 7 : 5;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: 'auto' };
  }

  _t(key, vars) {
    return gsT(gsLang(this._hass, this._config), key, vars);
  }

  _n(key, n, vars) {
    return gsN(gsLang(this._hass, this._config), key, n, vars);
  }

  // "3 minutes ago", "yesterday"… in the card's language.
  _ago(iso) {
    const m = gsMinutes(iso);
    let rtf;
    try {
      rtf = new Intl.RelativeTimeFormat(gsLang(this._hass, this._config), { numeric: 'auto' });
    } catch {
      return '';
    }
    if (m < 1) return rtf.format(0, 'second');
    if (m < 60) return rtf.format(-Math.floor(m), 'minute');
    if (m < 1440) return rtf.format(-Math.floor(m / 60), 'hour');
    return rtf.format(-Math.floor(m / 1440), 'day');
  }

  _absolute(iso) {
    const d = new Date(iso);
    if (!Number.isFinite(d.getTime())) return '';
    try {
      return d.toLocaleString(gsLang(this._hass, this._config), { dateStyle: 'medium', timeStyle: 'short' });
    } catch {
      return d.toISOString();
    }
  }

  // The entities of the chosen sensor's device, or of the first Git Sync device.
  _resolve() {
    const hass = this._hass;
    const devices = gsDevices(hass?.entities);
    if (this._config.entity) {
      const device = hass?.entities?.[this._config.entity]?.device_id || '';
      return { ...(devices[device] || {}), status: this._config.entity, device };
    }
    const [device, ids] = Object.entries(devices).find(([, d]) => d.status) || [];
    return ids ? { ...ids, device } : null;
  }

  _toast(message) {
    this.dispatchEvent(new CustomEvent('hass-notification', { detail: { message }, bubbles: true, composed: true }));
  }

  async _call(service) {
    const data = {};
    const entry = this._hass?.devices?.[this._ids?.device]?.config_entries?.[0];
    if (entry) data.config_entry_id = entry;
    if (service === 'commit_push') {
      const message = this._draft.trim();
      if (message) data.message = message;
    }
    this._busy = service;
    this._confirm = false;
    this._draft = '';
    this._render();
    try {
      // callService(domain, service, data, target, notifyOnError, returnResponse)
      const result = await this._hass.callService('git_sync', service, data, undefined, false, true);
      const first = result?.response?.results?.[0];
      if (service === 'commit_push') {
        if (first?.committed) this._toast(this._t('committed', { m: first.message }));
        else this._toast(this._t(first?.pushed ? 'pushed' : 'nothing'));
      }
      else this._toast(this._n('exported', first?.files?.length ?? 0));
    } catch (err) {
      this._toast(this._t('failed', { e: err?.message || String(err) }));
    } finally {
      this._busy = null;
      this._render();
    }
  }

  // Asks the AI task for a message describing the current changes, without committing, and puts it in the field.
  async _generate() {
    if (this._generating) return;
    const data = {};
    const entry = this._hass?.devices?.[this._ids?.device]?.config_entries?.[0];
    if (entry) data.config_entry_id = entry;
    this._generating = true;
    this._render();
    try {
      const result = await this._hass.callService('git_sync', 'generate_message', data, undefined, false, true);
      const message = result?.response?.message;
      // The popup may have been closed meanwhile: a late message must not come back at the next opening.
      if (message) {
        if (this._confirm) this._draft = message;
      } else this._toast(this._t('generated_none'));
    } catch (err) {
      this._toast(this._t('failed', { e: err?.message || String(err) }));
    } finally {
      this._generating = false;
      if (this._confirm) {
        this._render();
        this.shadowRoot.querySelector('#message')?.focus?.();
      }
    }
  }

  _bind() {
    const root = this.shadowRoot;
    const on = (sel, fn) => root.querySelector(sel)?.addEventListener('click', fn);
    const toggleFiles = () => {
      this._filesOpen = !this._filesOpen;
      this._render();
    };
    on('.toggle', toggleFiles);
    root.querySelector('.toggle')?.addEventListener('keydown', (ev) => {
      if (ev.key !== 'Enter' && ev.key !== ' ') return;
      ev.preventDefault();
      toggleFiles();
    });
    on('#commit', () => {
      this._confirm = true;
      this._render();
      root.querySelector('#message')?.focus?.();
    });
    on('#export', () => this._call('export_dashboards'));
    const close = () => {
      this._confirm = false;
      this._draft = '';
      this._render();
    };
    on('#cancel', close);
    on('.overlay', close);
    on('#confirm', () => {
      if (!this._generating) this._call('commit_push');
    });
    on('#generate', () => this._generate());
    root.querySelector('#message')?.addEventListener('input', (ev) => {
      this._draft = ev.target?.value ?? '';
    });
    root.querySelector('#message')?.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter' && !this._generating) this._call('commit_push');
      if (ev.key === 'Escape') close();
    });
  }

  // The element with the keyboard focus, as a selector to find it again after a render replaced the DOM.
  _focused() {
    const el = this.shadowRoot?.activeElement;
    if (!el) return null;
    if (el.id) return `#${el.id}`;
    return el.classList?.contains('toggle') ? '.toggle' : null;
  }

  _render() {
    const focused = this._focused();
    this._paint();
    if (focused) this.shadowRoot.querySelector(focused)?.focus?.();
  }

  _paint() {
    if (!this._config || !this.shadowRoot) return;
    const hass = this._hass;
    if (!hass) return;
    const ids = this._resolve();
    this._ids = ids;
    this._sigMinute = Math.floor(Date.now() / 60000);
    this._sig = true;
    const statusObj = ids && hass.states[ids.status];
    if (!statusObj) {
      this.shadowRoot.innerHTML = `<style>${this._css()}</style><ha-card><div class="empty">${gsEsc(this._t('not_loaded'))}</div></ha-card>`;
      return;
    }

    const c = this._config;
    const a = statusObj.attributes || {};
    const status = GS_STATUSES.includes(statusObj.state) ? statusObj.state : 'unavailable';
    const files = Array.isArray(a.changed_files) ? a.changed_files : [];
    const count = Number(a.changed_count ?? files.length) || 0;
    const valid = (s) => s && !['unknown', 'unavailable'].includes(s.state);
    const commitObj = hass.states[ids.last_commit];
    const pushObj = hass.states[ids.last_push];
    const exportObj = hass.states[ids.last_export];
    const busy = this._busy;
    const subtitle = [a.branch, gsRepo(a.remote_url)].filter(Boolean).map(gsEsc).join(' → ');

    const commit = valid(commitObj)
      ? `<div class="commit">
          <div class="lbl">${gsEsc(this._t('last_commit'))}</div>
          <div class="msg">${gsEsc(commitObj.attributes?.message)}</div>
          <div class="meta"><span class="sha">${gsEsc(commitObj.attributes?.short_sha)}</span>
            <span title="${gsEsc(this._absolute(commitObj.state))}">${gsEsc(this._ago(commitObj.state))}</span></div>
        </div>`
      : '';

    const timeRow = (icon, label, obj, extra = '') => `
      <div class="row">
        <ha-icon icon="${icon}"></ha-icon>
        <span class="label">${gsEsc(label)}</span>
        <span class="value" title="${valid(obj) ? gsEsc(this._absolute(obj.state)) : ''}">${
          valid(obj) ? gsEsc(this._ago(obj.state)) : gsEsc(this._t('never'))
        }${extra}</span>
      </div>`;

    let changes;
    if (c.show_files && count > 0) {
      const list = this._filesOpen
        ? `<ul class="files">${files
            .slice(0, GS_FILES_SHOWN)
            .map((f) => `<li title="${gsEsc(f)}">${gsEsc(f)}</li>`)
            .join('')}${count > GS_FILES_SHOWN ? `<li>${gsEsc(this._t('more', { n: count - GS_FILES_SHOWN }))}</li>` : ''}</ul>`
        : '';
      changes = `<div class="row toggle" role="button" tabindex="0" aria-expanded="${this._filesOpen}">
          <ha-icon class="chevron${this._filesOpen ? ' open' : ''}" icon="mdi:chevron-right"></ha-icon>
          <span class="label">${gsEsc(this._t('changed_files'))}</span>
          <span class="value">${gsEsc(this._n('files', count))}</span>
        </div>${list}`;
    } else {
      changes = `<div class="row">
          <ha-icon icon="mdi:file-document-multiple-outline"></ha-icon>
          <span class="label">${gsEsc(this._t('changes'))}</span>
          <span class="value">${gsEsc(count > 0 ? this._n('files', count) : this._t('no_changes'))}</span>
        </div>`;
    }

    const exportCount = exportObj?.attributes?.files?.length || 0;
    const exportRow = c.show_export
      ? timeRow(
          'mdi:view-dashboard-outline',
          this._t('last_export'),
          exportObj,
          valid(exportObj) && exportCount ? ` · ${gsEsc(this._n('files', exportCount))}` : '',
        )
      : '';

    const popup = this._confirm
      ? `<div class="overlay"></div>
        <div class="popup" role="dialog" aria-modal="true">
          <div class="p-title">${gsEsc(this._t('confirm_title'))}</div>
          <div class="p-text">${gsEsc(count > 0 ? this._n('confirm_text', count) : this._t('confirm_push'))}</div>
          <div class="field${this._generating ? ' generating' : ''}">
            <input id="message" type="text" maxlength="100" autocomplete="off" aria-label="${gsEsc(this._t('message', { branch: a.branch || 'HEAD' }))}"
              placeholder="${gsEsc(this._t('message', { branch: a.branch || 'HEAD' }))}" value="${gsEsc(this._draft)}"${this._generating ? ' disabled' : ''} />
            ${
              a.ai_task
                ? `<button class="gen" id="generate" title="${gsEsc(this._t('generate'))}" aria-label="${gsEsc(this._t('generate'))}"${this._generating ? ' disabled' : ''}>
                    <ha-icon icon="${this._generating ? 'mdi:loading' : 'mdi:creation-outline'}"></ha-icon></button>`
                : ''
            }
          </div>
          ${a.ai_task ? `<div class="hint">${gsEsc(this._t('message_hint'))}</div>` : ''}
          <div class="actions">
            <button class="action" id="cancel"><ha-icon icon="mdi:close"></ha-icon>${gsEsc(this._t('cancel'))}</button>
            <button class="action" id="confirm"${this._generating ? ' disabled' : ''}><ha-icon icon="mdi:source-commit-end"></ha-icon>${gsEsc(this._t('commit'))}</button>
          </div>
        </div>`
      : '';

    const canCommit = ['dirty', 'ahead', 'error'].includes(status) && !busy;
    const button = (id, service, icon, label, enabled) =>
      `<button class="action${busy === service ? ' busy' : ''}" id="${id}" ${enabled ? '' : 'disabled'}>
        <ha-icon icon="${busy === service ? 'mdi:loading' : icon}"></ha-icon>${gsEsc(label)}</button>`;

    this.shadowRoot.innerHTML = `
      <style>${this._css()}</style>
      <ha-card class="st-${status}">
        <div class="header">
          <div class="badge"><ha-icon icon="mdi:git"></ha-icon></div>
          <div class="titles">
            <div class="title">${gsEsc(c.title || this._t('title'))}</div>
            <div class="subtitle">${subtitle}</div>
          </div>
          <span class="pill${busy ? ' busy' : ''}">${gsEsc(busy ? this._t('working') : this._t(status))}</span>
        </div>
        ${commit}
        <div class="rows">
          ${changes}
          ${timeRow('mdi:cloud-check-outline', this._t('last_push'), pushObj)}
          ${exportRow}
        </div>
        ${a.last_error ? `<div class="err">${gsEsc(a.last_error)}</div>` : ''}
        <div class="actions">
          ${button('commit', 'commit_push', 'mdi:source-commit-end', this._t('commit'), canCommit)}
          ${c.show_export ? button('export', 'export_dashboards', 'mdi:export', this._t('export'), !busy) : ''}
        </div>
        ${popup}
      </ha-card>`;
    this._bind();
  }

  _css() {
    return `
      :host { --gs-ok: var(--success-color, #43a047); --gs-warn: var(--warning-color, #ffa600);
              --gs-info: var(--info-color, #039be5); --gs-alert: var(--error-color, #db4437);
              --gs-off: var(--disabled-text-color, #9e9e9e); --gs-accent: var(--primary-color, #03a9f4); }
      ha-card { position: relative; overflow: hidden; padding: 16px; --s: var(--gs-off); }
      ha-card.st-clean { --s: var(--gs-ok); }
      ha-card.st-dirty { --s: var(--gs-warn); }
      ha-card.st-ahead { --s: var(--gs-info); }
      ha-card.st-error { --s: var(--gs-alert); }
      .empty { padding: 8px 0; color: var(--secondary-text-color); }

      .header { display: flex; align-items: center; gap: 12px; }
      .badge { flex: none; width: 40px; height: 40px; border-radius: 50%; display: grid; place-items: center;
               color: var(--s); background: color-mix(in srgb, var(--s) 18%, transparent); }
      .badge ha-icon { --mdc-icon-size: 22px; }
      .titles { flex: 1; min-width: 0; }
      .title { font-size: 16px; font-weight: 500; line-height: 22px; color: var(--primary-text-color); }
      .subtitle { font-size: 12px; line-height: 16px; color: var(--secondary-text-color);
                  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .pill { flex: none; align-self: flex-start; margin-top: 2px; display: inline-flex; align-items: center; gap: 6px;
              padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 500;
              color: var(--s); background: color-mix(in srgb, var(--s) 14%, transparent); }
      .pill::before { content: ''; width: 7px; height: 7px; border-radius: 50%; background: var(--s); }
      .pill.busy::before { animation: gs-pulse 1s ease-in-out infinite; }

      .commit { margin-top: 14px; padding: 10px 12px; border-radius: 12px;
                background: var(--secondary-background-color, rgba(127,127,127,.08)); }
      .commit .lbl { font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: var(--secondary-text-color); }
      .commit .msg { margin-top: 2px; font-size: 14px; line-height: 20px; color: var(--primary-text-color); word-break: break-word; }
      .commit .meta { margin-top: 4px; font-size: 12px; color: var(--secondary-text-color); display: flex; gap: 8px; flex-wrap: wrap; }
      .sha { font-family: var(--code-font-family, monospace); }

      .rows { margin-top: 10px; display: flex; flex-direction: column; }
      .row { display: flex; align-items: center; gap: 10px; min-height: 36px; font-size: 14px; }
      .row ha-icon { --mdc-icon-size: 20px; color: var(--secondary-text-color); flex: none; }
      .row .label { flex: 1; color: var(--primary-text-color); }
      .row .value { color: var(--secondary-text-color); text-align: right; }
      .row.toggle { cursor: pointer; user-select: none; }
      .row.toggle:focus-visible { outline: 2px solid var(--gs-accent); outline-offset: 2px; border-radius: 6px; }
      .chevron { transition: transform .2s ease; }
      .chevron.open { transform: rotate(90deg); }
      .files { margin: 2px 0 6px 30px; padding: 0; list-style: none; max-height: 180px; overflow-y: auto;
               font-family: var(--code-font-family, monospace); font-size: 12px; line-height: 18px; color: var(--secondary-text-color); }
      .files li { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

      .err { margin-top: 8px; padding: 8px 10px; border-radius: 10px; font-size: 12px; word-break: break-word;
             color: var(--gs-alert); background: color-mix(in srgb, var(--gs-alert) 10%, transparent); }

      .actions { margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
      button.action { flex: 1 1 auto; display: inline-flex; align-items: center; justify-content: center; gap: 6px;
                      white-space: nowrap; min-height: 38px; padding: 0 14px; border-radius: 10px; cursor: pointer;
                      font: inherit; font-size: 14px; font-weight: 500; color: var(--gs-accent); background: transparent;
                      border: 1px solid color-mix(in srgb, var(--gs-accent) 45%, transparent); transition: background .15s ease; }
      button.action ha-icon { --mdc-icon-size: 18px; flex: none; }
      button.action:hover:not([disabled]) { background: color-mix(in srgb, var(--gs-accent) 10%, transparent); }
      button.action:focus-visible { outline: 2px solid var(--gs-accent); outline-offset: 2px; }
      button.action[disabled] { cursor: default; opacity: .45; }
      button.action.busy ha-icon { animation: gs-spin 1s linear infinite; }

      .overlay { position: absolute; inset: 0; z-index: 2; backdrop-filter: blur(2px);
                 background: color-mix(in srgb, var(--card-background-color, #fff) 55%, transparent); }
      .popup { position: absolute; top: 12px; left: 12px; right: 12px; z-index: 3; padding: 16px; border-radius: 14px;
               background: var(--card-background-color, #fff); box-shadow: 0 8px 28px rgba(0,0,0,.25);
               border: 1px solid var(--divider-color, rgba(127,127,127,.2)); }
      .p-title { font-size: 16px; font-weight: 500; color: var(--primary-text-color); }
      .p-text { margin-top: 4px; font-size: 13px; color: var(--secondary-text-color); }
      /* VS Code-like message box: placeholder with the branch, sparkle button inside, on the right */
      .field { position: relative; margin-top: 12px; }
      .field input { box-sizing: border-box; width: 100%; padding: 9px 40px 9px 10px; border-radius: 8px;
                     font: inherit; font-size: 14px; color: var(--primary-text-color); outline: none;
                     background: var(--secondary-background-color, transparent);
                     border: 1px solid var(--divider-color, rgba(127,127,127,.3)); text-overflow: ellipsis; }
      .field input::placeholder { color: var(--secondary-text-color); opacity: .8; }
      .field input:focus { border-color: var(--gs-accent); }
      .field input[disabled] { opacity: .6; }
      .gen { position: absolute; top: 50%; right: 4px; transform: translateY(-50%); width: 32px; height: 32px;
             display: grid; place-items: center; padding: 0; border: none; border-radius: 6px; cursor: pointer;
             background: transparent; color: var(--secondary-text-color); transition: color .15s ease, background .15s ease; }
      .gen ha-icon { --mdc-icon-size: 18px; }
      .gen:hover:not([disabled]) { color: var(--gs-accent); background: color-mix(in srgb, var(--gs-accent) 10%, transparent); }
      .gen:focus-visible { outline: 2px solid var(--gs-accent); outline-offset: 1px; }
      .gen[disabled] { cursor: default; }
      .generating .gen ha-icon { animation: gs-spin 1s linear infinite; color: var(--gs-accent); }
      .hint { margin-top: 4px; font-size: 11px; color: var(--secondary-text-color); }
      .popup .actions { margin-top: 14px; }

      @keyframes gs-spin { to { transform: rotate(360deg); } }
      @keyframes gs-pulse { 50% { opacity: .3; } }
      @media (prefers-reduced-motion: reduce) {
        .pill.busy::before, button.action.busy ha-icon, .generating .gen ha-icon { animation: none; }
        .chevron, button.action, .gen { transition: none; }
      }
    `;
  }
}

// ── Editor ───────────────────────────────────────────────────────────────────
const GS_HELPERS = ['entity', 'title', 'show_files', 'show_export', 'language'];

class GitSyncCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._update();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  _update() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement('ha-form');
      const t = (key) => gsT(gsLang(this._hass, this._config), key);
      this._form.computeLabel = (s) => t(`ed_${s.name}`);
      this._form.computeHelper = (s) => (GS_HELPERS.includes(s.name) ? t(`ed_${s.name}_helper`) : undefined);
      this._form.addEventListener('value-changed', (ev) => {
        const config = { ...ev.detail.value };
        // Options left at their default are not written to the YAML.
        for (const k of Object.keys(config)) {
          if (config[k] === '' || config[k] == null || GS_DEFAULTS[k] === config[k]) delete config[k];
        }
        this.dispatchEvent(new CustomEvent('config-changed', { detail: { config }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    const c = this._config;
    const lang = gsLang(this._hass, c);
    // Reassigning the schema at every Home Assistant update would re-render ha-form while the user is typing.
    if (this._deps && this._deps.config === c && this._deps.lang === lang) return;
    this._deps = { config: c, lang };
    this._form.data = { ...GS_DEFAULTS, ...c };
    this._form.schema = [
      { name: 'entity', selector: { entity: { filter: { integration: 'git_sync', domain: 'sensor' } } } },
      { name: 'title', selector: { text: {} } },
      { name: 'show_files', selector: { boolean: {} } },
      { name: 'show_export', selector: { boolean: {} } },
      {
        name: 'language',
        selector: {
          select: {
            mode: 'dropdown',
            options: [
              { value: 'en', label: 'English' },
              { value: 'fr', label: 'Français' },
              { value: 'de', label: 'Deutsch' },
              { value: 'es', label: 'Español' },
            ],
          },
        },
      },
    ];
  }
}

if (!customElements.get('git-sync-card')) {
  customElements.define('git-sync-card', GitSyncCard);
  customElements.define('git-sync-card-editor', GitSyncCardEditor);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: 'git-sync-card',
    name: 'Git Sync Card',
    description: 'Git status of the configuration, Commit & push and dashboard export',
    preview: true,
    documentationURL: 'https://github.com/juju35/ha-git-sync',
  });
  console.info(`%c GIT-SYNC-CARD %c v${GIT_SYNC_CARD_VERSION} `, 'background:#f05133;color:#fff;font-weight:700', '');
}
