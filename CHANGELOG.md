# Changelog

## 1.5.0 - 2026-11-07

### What's new
- New action `git_sync.pull` (administrators only) that brings in the remote commits, by fast-forward or by rebasing the local commits on a clean work tree, and a **Pull** button in the card and the mini card when the status is `behind`.

### Security
- The secret guard now checks the files really staged by `git add -A` as well: a sensitive file written between the check and the staging is unstaged and the commit is refused.

### Fixes
- An automatic commit refused for a sensitive file or blocked by the remote is logged once as a warning, without a traceback, and is not retried until the changed files or the commits ahead or behind change.
- The notification image content type is taken from the URL path, so an image URL with a query string (`…/git.png?v=2`) gives `png`.

## 1.4.0 - 2026-11-07

### What's new
- Diagnostics: **Download diagnostics** now gives the entry settings and the last status, with the SSH key path, the commit author name and email and the credentials of an HTTPS remote URL redacted.

## 1.3.0 - 2026-11-07

### What's new
- **Behind and diverged**: the remote is now fetched during the status refresh (every 15 minutes by default, new *Remote check interval* option, 0 to disable) and before each commit, so the `behind` count is current. The status sensor and the card's status pill gain the `behind` and `diverged` states.
- **Pull before push** (new option, on by default): when the remote has new commits, the commit is rebased on them (`git pull --rebase --autostash`) before the push. A diverged branch is neither committed nor pushed, and a rebase conflict is aborted (`git rebase --abort`) without pushing; both raise a clear error and a repair explaining how to resolve it, removed by the next successful push.
- **Secret guard**: a commit, and the AI message generation, are refused when the changes include `secrets.yaml`, `.storage/`, `.ssh/`, `*.pem`, `*.key`, `id_rsa*`, `known_devices.yaml`, `home-assistant_v2.db*` or `*.log` (new *Allow tracked sensitive files* option for the ones already tracked). The values of `password`, `token`, `api_key`, `secret` and `client_secret` keys are hidden from the diff sent to the AI task.
- New repair when `.gitignore` does not exclude `secrets.yaml` and `.storage/`: its fix shows the lines to add and appends them once an administrator confirms.

## 1.2.1 - 2026-11-07

### Security
- The `git_sync` actions (`commit_push`, `export_dashboards`, `generate_message`, `get_diff`, `generate_ssh_key`) now require an administrator: a non-admin user could read the diff, `secrets.yaml` included, or commit, push and create the SSH key. Automations, scripts and the card used by an administrator work as before.

## 1.2.0 - 2026-11-07

### What's new
- **Diff viewer** in the card: the **View changes** button (beside Commit & push and Export dashboards, in the mini card's footer, and as a link in the commit confirmation) opens a full-screen view of what the next commit would include, file by file like an editor's source control view. The files on the left with their status letter (added, modified, deleted, renamed, mode) and their added and removed lines; the selected file on the right hunk by hunk, with the line numbers of both sides, additions in green and deletions in red, renames with their old path, binary files and cut patches flagged. Full screen on a phone, with the files as a row of chips above the diff. ↑ ↓ walk the files, Escape or a click outside closes, **Commit & push** goes straight to the commit confirmation. Translated in every language of the card.
- New action `git_sync.get_diff`: the same changes, file by file (status, old path, binary, added and removed lines, hunks with both line numbers), computed on a copy of the Git index so nothing is staged or committed. At most 2000 lines per file and 200 files per response, the rest counted.

## 1.1.2 - 2026-11-04

### Documentation
- README: images and links use absolute URLs, so the screenshots, icons, badges and links display in HACS (relative paths broke there).
- README: screenshots get a display size, so cards no longer show oversized in HACS and on GitHub.

## 1.1.1 - 2026-11-04

### What's new
- Added Romanian, Danish, Swedish, Bulgarian, Russian, Ukrainian, Hungarian, Slovak, Czech, Slovenian, Latvian and Greek translations: the setup and options, the entities, the actions and both cards with their visual editor (`ro`, `da`, `sv`, `bg`, `ru`, `uk`, `hu`, `sk`, `cs`, `sl`, `lv` and `el`). The cards follow Home Assistant's language or the `language` option.
- AI commit messages can now be written in every language of the integration (22, Serbian in Cyrillic or Latin script), not only English, French, German and Spanish. The default still follows Home Assistant's language: its full tag first (`sr-Latn`, stored as `sr-latn`), then its language (`pt-BR` gives European Portuguese), else English.

## 1.1.0 - 2026-11-02

### What's new
- Mini card (`custom:git-sync-mini-card`): status, branch, last commit on one line, number of changed files, last push and Commit & push as an icon button, sized for 6 columns. Its zoom button at the top right switches it to the full card and back, and a click elsewhere brings back the compact view (not while a commit message is being written). In the compact view the commit message box takes the place of the content. The `zoom` option (visual editor) removes the button. Translated in every language of the card.

## 1.0.0 - 2026-11-02

First stable release. No change since 0.1.5.

## 0.1.5 - 2026-11-01

### Fixes
- Dashboard export: the cleanup only removes the files an earlier export wrote into the export folder. Before, it deleted every `lovelace*` file of the folder it had not just written, including your own YAML-mode dashboards such as `lovelace-energy.yaml`, and the automatic commit pushed the deletion. Nothing is removed from a folder the export never wrote to, nor on the first export after this update. A file the export wrote and you edited since (for example reused as a YAML-mode dashboard) is no longer deleted with its dashboard, and a file of yours that has the name of an export (`lovelace_resources.yaml`…) is no longer overwritten: it is skipped with a warning in the log.
- A push error no longer stays on the card once the commits have been pushed another way (for example `git push` in a terminal) and nothing is left to commit or push.
- File names with accents or other non-ASCII characters are listed as they are in the changed files (`été.yaml`, not `\303\251t\303\251.yaml`).
- Setup and repository settings: when Git does not know who signs the commits in the Home Assistant container, the form asks for the author email instead of creating an entry whose every commit fails with "Author identity unknown".
- Options: a notification action that does not exist is refused by the form instead of only writing a warning in the log at each commit.
- Card: choosing another Git Sync sensor in the visual editor (last commit, changed files…) no longer shows "Unavailable" with Commit & push disabled.
- Card: on a narrow card the title stays readable and truncates, the status pill shrinks to its coloured dot (its text stays in the tooltip), and long button labels (Polish, Serbian) wrap instead of overflowing the card or the confirmation popup.
- Card: the status pill and the error message are easier to read, in light and dark themes.
- Card: at 6 columns on a phone, the title keeps four letters, and a long value (last export in Polish or Serbian) goes under its label and wraps instead of being cut by the card. On wider cards the status pill shows its whole label instead of truncating it ("Re…").
- Card: inside a container sized to its content (layout-card, button-card, a grid column sized `auto`), the card no longer shrinks to a few pixels.
- Card: giving the keyboard focus back after an update no longer scrolls the page.

## 0.1.4 - 2026-11-01

### What's new
- Added Italian, Dutch, European Portuguese and Polish translations: the setup and options, the entities, the actions and the card with its visual editor (`it`, `nl`, `pt` and `pl`). The card follows Home Assistant's language or the `language` option; `pt-BR` uses the European Portuguese texts, in the integration and in the card, with Brazilian date formats. Commit messages are still written in English, French, German or Spanish.

## 0.1.3 - 2026-11-01

### What's new
- Added Serbian (Cyrillic and Latin) translations: the setup and options, the entities, the actions and the card with its visual editor (`sr` and `sr-Latn`). The card follows Home Assistant's language, in Latin script when Home Assistant is set to `sr-Latn`, or the `language` option. Commit messages are still written in English, French, German or Spanish.

## 0.1.2

### Fixes
- A repository set up as the README said (`git remote add`, no `git push -u`) is pushed: the first push sets the upstream. Before, every push failed with "no upstream branch", or, with a branch set, the commits waiting to be pushed were never noticed. A branch never pushed now shows "Push pending".
- A failed push is retried by the automatic commit, even when no file changed since.
- Commit & push with nothing new to commit pushes the pending commits and says so: the last push time is updated and the card shows "Pending commits pushed" instead of "Nothing to commit". The `git_sync.commit_push` response gains `pushed`.
- The user and token of an HTTPS remote (`https://user:token@…`) no longer appear in the `remote_url` attribute, nor in Git errors shown on the card or written to the logs.
- The notification action and image, and the branch and author in the repository settings, can be emptied again: an emptied field no longer comes back with its old value.
- The status refresh no longer takes Git's index lock, which could make a commit running at the same time fail.
- The dashboard export removes the files it no longer produces (deleted dashboard, format switched from JSON to YAML).
- `git_sync.generate_ssh_key`: the description of `config_entry_id` says the first repository is used, not all of them.
- Card: the changed files list opens with Enter or Space and the keyboard focus survives updates; Commit & push waits for the ✨ message being written, and a message arriving after the popup closed is dropped; a pending push no longer announces "0 changed files"; no chevron or button transition with reduced motion.

## 0.1.1

### What's new
- The AI task is preselected when Home Assistant has only one: when adding the integration, and in the options of an entry where it was never set. Without it, the card's ✨ button stayed hidden and commits used the generic message. Emptying the field keeps it empty.
- The commit message language defaults to the language of Home Assistant (English, French, German or Spanish).

## 0.1.0

### What's new
- First release: Git status of the Home Assistant configuration (clean, changes pending, push pending, error) with the changed files, branch and remote.
- Automatic commit and push at a set interval when something changed, and on demand from the **Commit and push** button, the `git_sync.commit_push` action or the card.
- Commit messages written by an `ai_task` entity from the staged diff, in Conventional Commits format, in English, French, German or Spanish, with a generic message when no AI task is set or it fails.
- `git_sync.generate_message` action: writes a commit message for the current changes without committing, on a copy of the Git index.
- Notification after each commit, with an optional image.
- Dashboard export from `.storage` to a folder, as JSON, YAML or both, daily at a set time and optionally before each commit; `git_sync.export_dashboards` action and **Export dashboards** button.
- `git_sync.generate_ssh_key` action creating the deploy key; the push accepts the host key on first use.
- `git_sync_committed` and `git_sync_exported` events.
- **Git Sync Card**, bundled with the integration and added to the dashboard resources automatically: status, last commit, collapsible changed files, last push and export, Commit & push with a confirmation and a VS Code-like message box (branch in the placeholder, ✨ button writing the message with the AI task, Enter to commit), Export dashboards. Visual editor; English, French, German and Spanish.

### Maintenance
- Tests on the latest Home Assistant and on 2024.12, card unit tests, pre-commit, Ruff, Biome, jscpd and vulture, HACS and hassfest validation, and a Screenshots workflow that renders the README captures (light and dark) on pull requests.
