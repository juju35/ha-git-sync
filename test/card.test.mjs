// Unit tests for the card: the card file is evaluated with stubs, no browser needed.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../custom_components/git_sync/frontend/git-sync-card.js', import.meta.url), 'utf8');

// Elements found in the rendered HTML by an id or class: enough to click the buttons and type a message.
// They also track the shadow root's activeElement, to check that a re-render keeps the keyboard focus.
const fakeElement = (root, sel) => ({
  handlers: {},
  value: '',
  id: sel.startsWith('#') ? sel.slice(1) : '',
  classList: { contains: (c) => sel === `.${c}` },
  addEventListener(type, fn) {
    this.handlers[type] = fn;
  },
  click() {
    this.handlers.click?.({});
  },
  key(key) {
    const ev = { key, prevented: false, preventDefault() {
      this.prevented = true;
    } };
    this.handlers.keydown?.(ev);
    return ev;
  },
  focus() {
    root.activeElement = this;
  },
});
const fakeNode = () => ({
  innerHTML: '',
  style: {},
  handlers: {},
  addEventListener(type, fn) {
    this.handlers[type] = fn;
  },
  appendChild() {},
  dispatch(value) {
    this.handlers['value-changed']({ detail: { value } });
  },
  attachShadow() {
    const elements = {};
    const root = {
      innerHTML: '',
      elements,
      querySelector: (sel) => {
        const html = root.innerHTML;
        const present = sel.startsWith('#') ? html.includes(`id="${sel.slice(1)}"`) : html.includes(`class="${sel.slice(1)}`) || html.includes(` ${sel.slice(1)}"`);
        if (!present) return null;
        elements[sel] ||= fakeElement(root, sel);
        return elements[sel];
      },
    };
    // Each render replaces the DOM: forget the elements of the previous one.
    let inner = '';
    Object.defineProperty(root, 'innerHTML', {
      get: () => inner,
      set: (v) => {
        inner = v;
        root.activeElement = null;
        for (const k of Object.keys(elements)) delete elements[k];
      },
    });
    this.shadowRoot = root;
    return root;
  },
});

const context = {
  HTMLElement: class {},
  customElements: { get: () => true, define() {} },
  window: {},
  document: { createElement: () => fakeNode() },
  CustomEvent: class {
    constructor(type, init) {
      this.type = type;
      this.detail = init?.detail;
    }
  },
  Intl,
  console,
  Date,
};
vm.createContext(context);
vm.runInContext(
  `${source}\nthis.gs = { GitSyncCard, GitSyncCardEditor, GS_I18N, gsEsc, gsLang, gsDevices, gsRepo, GS_DEFAULTS };`,
  context,
);
const { GitSyncCard, GitSyncCardEditor, GS_I18N, gsEsc, gsLang, gsDevices, gsRepo } = context.gs;

const STATUS = 'sensor.git_sync_config_status';
const LAST_COMMIT = 'sensor.git_sync_config_last_commit';
const LAST_PUSH = 'sensor.git_sync_config_last_push';
const LAST_EXPORT = 'sensor.git_sync_config_last_export';
const COMMIT = 'button.git_sync_config_commit_and_push';

const minutesAgo = (m) => new Date(Date.now() - m * 60000).toISOString();

const REGISTRY = {
  [STATUS]: { platform: 'git_sync', device_id: 'd1', translation_key: 'status' },
  [LAST_COMMIT]: { platform: 'git_sync', device_id: 'd1', translation_key: 'last_commit' },
  [LAST_PUSH]: { platform: 'git_sync', device_id: 'd1', translation_key: 'last_push' },
  [LAST_EXPORT]: { platform: 'git_sync', device_id: 'd1', translation_key: 'last_export' },
  [COMMIT]: { platform: 'git_sync', device_id: 'd1', translation_key: 'commit_push' },
  'sensor.other': { platform: 'demo', device_id: 'd2' },
};

function makeHass({ status = 'clean', files = [], error = null, language = 'en', response, aiTask = null } = {}) {
  const calls = [];
  return {
    calls,
    language,
    entities: REGISTRY,
    devices: { d1: { config_entries: ['entry1'] } },
    states: {
      [STATUS]: {
        state: status,
        attributes: {
          branch: 'main',
          remote_url: 'git@github.com:me/homeassistant-config.git',
          changed_count: files.length,
          changed_files: files,
          last_error: error,
          ai_task: aiTask,
        },
      },
      [LAST_COMMIT]: {
        state: minutesAgo(42),
        attributes: { message: 'feat(corridor): lower the night light threshold', short_sha: '3f9c2ab' },
      },
      [LAST_PUSH]: { state: minutesAgo(42), attributes: { message: 'x' } },
      [LAST_EXPORT]: { state: 'unknown', attributes: {} },
    },
    callService: async (...args) => {
      calls.push(args);
      return { response: response ?? { results: [{ committed: true, message: 'fix: typo' }] } };
    },
  };
}

function render(config, hass) {
  const card = new GitSyncCard();
  card.attachShadow = fakeNode().attachShadow;
  card.style = {};
  card.toasts = [];
  card.dispatchEvent = (ev) => card.toasts.push(ev.detail?.message);
  card.setConfig(config);
  card.hass = hass;
  return card;
}

const html = (card) => card.shadowRoot.innerHTML;

test('every language has the English keys', () => {
  const keys = Object.keys(GS_I18N.en).sort();
  for (const [lang, strings] of Object.entries(GS_I18N)) {
    assert.deepEqual(Object.keys(strings).sort(), keys, lang);
  }
});

test('language follows Home Assistant, then the config, with English as fallback', () => {
  assert.equal(gsLang({ language: 'fr-FR' }, {}), 'fr');
  assert.equal(gsLang({ language: 'fr' }, { language: 'de' }), 'de');
  assert.equal(gsLang({ language: 'ja' }, {}), 'en');
});

test('entities found by translation key, or by entity ID when it is missing', () => {
  assert.equal(gsDevices(REGISTRY).d1.status, STATUS);
  assert.equal(gsDevices(REGISTRY).d1.commit_push, COMMIT);
  const noKeys = Object.fromEntries(Object.entries(REGISTRY).map(([id, e]) => [id, { ...e, translation_key: undefined }]));
  assert.equal(gsDevices(noKeys).d1.last_commit, LAST_COMMIT);
  assert.equal(gsDevices(noKeys).d1.commit_push, COMMIT);
  assert.equal(gsDevices(noKeys).d2, undefined);
});

test('remote URL shortened to owner/repository', () => {
  assert.equal(gsRepo('git@github.com:me/homeassistant-config.git'), 'me/homeassistant-config');
  assert.equal(gsRepo('https://github.com/me/ha.git'), 'me/ha');
  assert.equal(gsRepo(''), '');
});

test('HTML is escaped', () => {
  assert.equal(gsEsc('<b>"x"</b>'), '&lt;b&gt;&quot;x&quot;&lt;/b&gt;');
});

test('clean repository: status, last commit, commit disabled', () => {
  const out = html(render({}, makeHass()));
  assert.match(out, /st-clean/);
  assert.match(out, /Up to date/);
  assert.match(out, /main → me\/homeassistant-config/);
  assert.match(out, /lower the night light threshold/);
  assert.match(out, /3f9c2ab/);
  assert.match(out, /42 minutes ago/);
  assert.match(out, /Working tree clean/);
  assert.match(out, /Dashboard export[\s\S]*Never/);
  assert.match(out, /id="commit"\s+disabled/);
});

test('changes: files listed when expanded, commit enabled', () => {
  const card = render({}, makeHass({ status: 'dirty', files: ['automations.yaml', 'scripts.yaml'] }));
  assert.match(html(card), /st-dirty/);
  assert.match(html(card), /2 files/);
  assert.doesNotMatch(html(card), /automations\.yaml/);
  card.shadowRoot.querySelector('.toggle').click();
  assert.match(html(card), /<li title="automations.yaml">automations.yaml<\/li>/);
  assert.doesNotMatch(html(card), /id="commit"\s+disabled/);
});

test('show_files and show_export can be turned off', () => {
  const out = html(render({ show_files: false, show_export: false }, makeHass({ status: 'dirty', files: ['a.yaml'] })));
  assert.doesNotMatch(out, /class="row toggle"/);
  assert.match(out, /1 file/);
  assert.doesNotMatch(out, /<span class="label">Dashboard export/);
  assert.doesNotMatch(out, /id="export"/);
});

test('error is shown', () => {
  const out = html(render({}, makeHass({ status: 'error', error: 'git push failed: <denied>' })));
  assert.match(out, /st-error/);
  assert.match(out, /git push failed: &lt;denied&gt;/);
});

test('commit asks for confirmation, then calls the action with the message', async () => {
  const hass = makeHass({ status: 'dirty', files: ['a.yaml'] });
  const card = render({}, hass);
  card.shadowRoot.querySelector('#commit').click();
  assert.match(html(card), /Commit and push now\?/);
  assert.match(html(card), /1 changed file will be committed/);
  card.shadowRoot.querySelector('#message').handlers.input({ target: { value: '  fix: typo ' } });
  card.shadowRoot.querySelector('#confirm').click();
  await new Promise((r) => setTimeout(r, 0));
  assert.deepEqual(JSON.parse(JSON.stringify(hass.calls[0])), [
    'git_sync',
    'commit_push',
    { config_entry_id: 'entry1', message: 'fix: typo' },
    null,
    false,
    true,
  ]);
  assert.deepEqual(card.toasts, ['Committed: fix: typo']);
  assert.doesNotMatch(html(card), /Commit and push now/);
});

test('export button calls the export action', async () => {
  const hass = makeHass({ response: { results: [{ files: ['lovelace', 'lovelace.yaml'] }] } });
  const card = render({}, hass);
  card.shadowRoot.querySelector('#export').click();
  await new Promise((r) => setTimeout(r, 0));
  assert.equal(hass.calls[0][1], 'export_dashboards');
  assert.deepEqual(card.toasts, ['2 dashboard files exported']);
});

test('French', () => {
  const out = html(render({}, makeHass({ language: 'fr', status: 'dirty', files: ['a.yaml'] })));
  assert.match(out, /Modifications/);
  assert.match(out, /1 fichier/);
  assert.match(out, /Dernier push/);
});

test('not set up', () => {
  const card = render({}, { ...makeHass(), entities: {}, states: {} });
  assert.match(html(card), /Git Sync is not set up/);
});

test('editor drops options left at their default', () => {
  const editor = new GitSyncCardEditor();
  editor.appendChild = () => {};
  const events = [];
  editor.dispatchEvent = (ev) => events.push(ev.detail.config);
  editor.setConfig({});
  editor.hass = makeHass();
  editor._form.dispatch({ show_files: true, show_export: false, title: '' });
  assert.deepEqual(JSON.parse(JSON.stringify(events[0])), { show_export: false });
});

test('message box: branch in the placeholder, no sparkle button without AI task', () => {
  const card = render({}, makeHass({ status: 'dirty', files: ['a.yaml'] }));
  card.shadowRoot.querySelector('#commit').click();
  assert.match(html(card), /placeholder="Message \(Enter to commit on ‘main’\)"/);
  assert.doesNotMatch(html(card), /id="generate"/);
});

test('sparkle button generates the message into the field, without committing', async () => {
  const hass = makeHass({
    status: 'dirty',
    files: ['a.yaml'],
    aiTask: 'ai_task.google',
    response: { message: 'feat(lights): add the corridor scene' },
  });
  const card = render({}, hass);
  card.shadowRoot.querySelector('#commit').click();
  assert.match(html(card), /id="generate"/);
  card.shadowRoot.querySelector('#generate').click();
  assert.match(html(card), /class="field generating"/);
  await new Promise((r) => setTimeout(r, 0));
  assert.deepEqual(JSON.parse(JSON.stringify(hass.calls)), [
    ['git_sync', 'generate_message', { config_entry_id: 'entry1' }, null, false, true],
  ]);
  assert.match(html(card), /value="feat\(lights\): add the corridor scene"/);
  assert.match(html(card), /Commit and push now\?/);
  card.shadowRoot.querySelector('#confirm').click();
  await new Promise((r) => setTimeout(r, 0));
  assert.equal(hass.calls[1][1], 'commit_push');
  assert.equal(hass.calls[1][2].message, 'feat(lights): add the corridor scene');
});

test('sparkle button with nothing to describe shows a toast', async () => {
  const hass = makeHass({ status: 'dirty', files: ['a.yaml'], aiTask: 'ai_task.google', response: { message: null } });
  const card = render({}, hass);
  card.shadowRoot.querySelector('#commit').click();
  card.shadowRoot.querySelector('#generate').click();
  await new Promise((r) => setTimeout(r, 0));
  assert.deepEqual(card.toasts, ['Nothing to describe: no changes']);
  assert.match(html(card), /value=""/);
});

test('changed files expand from the keyboard (Enter and Space) and keep the focus', () => {
  const card = render({}, makeHass({ status: 'dirty', files: ['a.yaml'] }));
  const toggle = card.shadowRoot.querySelector('.toggle');
  toggle.focus();
  const ev = toggle.key('Enter');
  assert.equal(ev.prevented, true);
  assert.match(html(card), /<li title="a.yaml">/);
  assert.match(html(card), /aria-expanded="true"/);
  // Re-rendered by innerHTML: the new toggle has the focus.
  assert.equal(card.shadowRoot.activeElement, card.shadowRoot.querySelector('.toggle'));
  card.shadowRoot.querySelector('.toggle').key(' ');
  assert.doesNotMatch(html(card), /<li title="a.yaml">/);
  card.shadowRoot.querySelector('.toggle').key('a');
  assert.doesNotMatch(html(card), /<li title="a.yaml">/);
});

test('a Home Assistant update does not lose the keyboard focus', () => {
  const hass = makeHass({ status: 'dirty', files: ['a.yaml'] });
  const card = render({}, hass);
  card.shadowRoot.querySelector('#commit').focus();
  card.hass = makeHass({ status: 'dirty', files: ['a.yaml', 'b.yaml'] });
  assert.match(html(card), /2 files/);
  assert.equal(card.shadowRoot.activeElement?.id, 'commit');
});

test('push pending: the confirmation does not announce 0 changed files', () => {
  const card = render({}, makeHass({ status: 'ahead' }));
  card.shadowRoot.querySelector('#commit').click();
  assert.doesNotMatch(html(card), /0 changed files/);
  assert.match(html(card), /The commits waiting will be pushed\./);
  const fr = render({}, makeHass({ status: 'error', language: 'fr' }));
  fr.shadowRoot.querySelector('#commit').click();
  assert.match(html(fr), /Les commits en attente seront poussés\./);
});

test('push only: the toast says it was pushed, not "Nothing to commit"', async () => {
  const hass = makeHass({ status: 'ahead', response: { results: [{ committed: false, pushed: true, message: null }] } });
  const card = render({}, hass);
  card.shadowRoot.querySelector('#commit').click();
  card.shadowRoot.querySelector('#confirm').click();
  await new Promise((r) => setTimeout(r, 0));
  assert.deepEqual(card.toasts, ['Pending commits pushed']);
});

test('no commit while the message is being generated, and no stale message afterwards', async () => {
  let answer;
  const hass = makeHass({ status: 'dirty', files: ['a.yaml'], aiTask: 'ai_task.google' });
  hass.callService = (...args) => {
    hass.calls.push(args);
    return new Promise((resolve) => {
      answer = resolve;
    });
  };
  const card = render({}, hass);
  card.shadowRoot.querySelector('#commit').click();
  card.shadowRoot.querySelector('#generate').click();
  assert.match(html(card), /id="confirm"[^>]*disabled/);
  // Closed while generating: the late answer is not kept for the next opening.
  card.shadowRoot.querySelector('#cancel').click();
  answer({ response: { message: 'feat: late message' } });
  await new Promise((r) => setTimeout(r, 0));
  card.shadowRoot.querySelector('#commit').click();
  assert.match(html(card), /id="message"[^>]*value=""/);
  assert.doesNotMatch(html(card), /id="confirm"[^>]*disabled/);
});

test('reduced motion: no chevron or button transition', () => {
  const css = html(render({}, makeHass())).match(/@media \(prefers-reduced-motion: reduce\) \{([\s\S]*?\})\s*\}/)?.[1] || '';
  assert.match(css, /\.chevron/);
  assert.match(css, /transition: none/);
});
