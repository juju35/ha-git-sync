export const STATUS_COLORS = {
  clean: "var(--success-color, #43a047)",
  dirty: "var(--warning-color, #ffa600)",
  ahead: "var(--info-color, #039be5)",
  error: "var(--error-color, #db4437)",
  unavailable: "var(--disabled-text-color, #9e9e9e)",
};

export const STYLES = `
  :host { --gs-accent: var(--primary-color); }
  ha-card { position: relative; overflow: hidden; padding: 16px; }

  .header { display: flex; align-items: center; gap: 12px; }
  .badge {
    flex: none; width: 40px; height: 40px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    background: color-mix(in srgb, var(--gs-status) 18%, transparent);
    color: var(--gs-status);
  }
  .badge ha-icon { --mdc-icon-size: 22px; }
  .titles { flex: 1; min-width: 0; }
  .title { font-size: 16px; font-weight: 500; line-height: 22px; color: var(--primary-text-color); }
  .subtitle {
    font-size: 12px; line-height: 16px; color: var(--secondary-text-color);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .pill {
    flex: none; align-self: flex-start; margin-top: 2px;
    display: inline-flex; align-items: center; gap: 6px;
    padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 500;
    color: var(--gs-status);
    background: color-mix(in srgb, var(--gs-status) 14%, transparent);
  }
  .pill::before {
    content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--gs-status);
  }
  .pill.busy::before { animation: pulse 1s ease-in-out infinite; }

  .commit {
    margin-top: 14px; padding: 10px 12px; border-radius: 12px;
    background: var(--secondary-background-color, rgba(127,127,127,.08));
  }
  .commit-label { font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: var(--secondary-text-color); }
  .commit-message { margin-top: 2px; font-size: 14px; line-height: 20px; color: var(--primary-text-color); word-break: break-word; }
  .commit-meta { margin-top: 4px; font-size: 12px; color: var(--secondary-text-color); display: flex; gap: 8px; flex-wrap: wrap; }
  .sha { font-family: var(--code-font-family, monospace); }

  .rows { margin-top: 10px; display: flex; flex-direction: column; }
  .row { display: flex; align-items: center; gap: 10px; min-height: 36px; font-size: 14px; }
  .row ha-icon { --mdc-icon-size: 20px; color: var(--secondary-text-color); flex: none; }
  .row .label { flex: 1; color: var(--primary-text-color); }
  .row .value { color: var(--secondary-text-color); text-align: right; }
  .row.toggle { cursor: pointer; user-select: none; }
  .chevron { transition: transform .2s ease; }
  .chevron.open { transform: rotate(90deg); }

  .files {
    margin: 2px 0 6px 30px; padding: 0; list-style: none;
    font-family: var(--code-font-family, monospace); font-size: 12px; line-height: 18px;
    color: var(--secondary-text-color); max-height: 180px; overflow-y: auto;
  }
  .files li { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .error {
    margin-top: 8px; padding: 8px 10px; border-radius: 10px; font-size: 12px;
    color: var(--error-color, #db4437);
    background: color-mix(in srgb, var(--error-color, #db4437) 10%, transparent);
    word-break: break-word;
  }

  .actions { margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
  button.action {
    flex: 1 1 auto; display: inline-flex; white-space: nowrap; align-items: center; justify-content: center; gap: 6px;
    min-height: 38px; padding: 0 14px; border-radius: 10px; cursor: pointer;
    font: inherit; font-size: 14px; font-weight: 500;
    color: var(--gs-accent); background: transparent;
    border: 1px solid color-mix(in srgb, var(--gs-accent) 45%, transparent);
    transition: background .15s ease;
  }
  button.action ha-icon { --mdc-icon-size: 18px; flex: none; }
  button.action:hover:not([disabled]) { background: color-mix(in srgb, var(--gs-accent) 10%, transparent); }
  button.action[disabled] { cursor: default; opacity: .45; }
  button.action.busy ha-icon { animation: spin 1s linear infinite; }

  .overlay {
    position: absolute; inset: 0; z-index: 2;
    background: color-mix(in srgb, var(--card-background-color, #fff) 55%, transparent);
    backdrop-filter: blur(2px);
  }
  .popup {
    position: absolute; top: 12px; left: 12px; right: 12px; z-index: 3;
    padding: 16px; border-radius: 14px;
    background: var(--card-background-color, #fff);
    box-shadow: 0 8px 28px rgba(0,0,0,.25);
    border: 1px solid var(--divider-color, rgba(127,127,127,.2));
  }
  .popup-title { font-size: 16px; font-weight: 500; color: var(--primary-text-color); }
  .popup-text { margin-top: 4px; font-size: 13px; color: var(--secondary-text-color); }
  .popup label { display: block; margin-top: 12px; font-size: 12px; color: var(--secondary-text-color); }
  .popup input {
    box-sizing: border-box; width: 100%; margin-top: 4px; padding: 9px 10px; border-radius: 8px;
    font: inherit; font-size: 14px; color: var(--primary-text-color);
    background: var(--secondary-background-color, transparent);
    border: 1px solid var(--divider-color, rgba(127,127,127,.3)); outline: none;
  }
  .popup input:focus { border-color: var(--gs-accent); }
  .popup .hint { margin-top: 4px; font-size: 11px; color: var(--secondary-text-color); }
  .popup .actions { margin-top: 14px; }

  .warning { padding: 8px 0; color: var(--error-color, #db4437); }

  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes pulse { 50% { opacity: .3; } }
  @media (prefers-reduced-motion: reduce) {
    .pill.busy::before, button.action.busy ha-icon { animation: none; }
  }
`;
