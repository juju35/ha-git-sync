# Changelog

## 0.1.0

### What's new
- First release: Git status of the Home Assistant configuration (clean, changes pending, push pending, error) with the changed files, branch and remote.
- Automatic commit and push at a set interval when something changed, and on demand from the **Commit and push** button, the `git_sync.commit_push` action or the card.
- Commit messages written by an `ai_task` entity from the staged diff, in Conventional Commits format, in English, French, German or Spanish, with a generic message when no AI task is set or it fails.
- Notification after each commit, with an optional image.
- Dashboard export from `.storage` to a folder, as JSON, YAML or both, daily at a set time and optionally before each commit; `git_sync.export_dashboards` action and **Export dashboards** button.
- `git_sync.generate_ssh_key` action creating the deploy key; the push accepts the host key on first use.
- `git_sync_committed` and `git_sync_exported` events.
- **Git Sync Card**, bundled with the integration and added to the dashboard resources automatically: status, last commit, collapsible changed files, last push and export, Commit & push with a confirmation and an optional message, Export dashboards. Visual editor; English, French, German and Spanish.

### Maintenance
- Tests on the latest Home Assistant and on 2024.12, card unit tests, pre-commit, Ruff, Biome, jscpd and vulture, HACS and hassfest validation, and a Screenshots workflow that renders the README captures (light and dark) on pull requests.
