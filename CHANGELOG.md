# Changelog

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
