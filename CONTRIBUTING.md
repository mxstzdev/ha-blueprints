# Contributing

Thanks for helping to improve these blueprints! This guide is for everyone who
wants to change a blueprint or understand how the repository works. Users only
need the [README](README.md).

## What contributions are welcome

This collection is maintained by one person in their spare time, so pull
requests are limited to the blueprints that already exist:

| Welcome | Not accepted |
| --- | --- |
| Bug fixes | New blueprints |
| New features or options for an existing blueprint | Changes to CI, release tooling or repository structure |
| Documentation updates (README, comments, this guide) | Large rewrites without an issue discussed first |

Pull requests outside this scope will be closed, however good they are. If
you have an idea for a new blueprint, you are welcome to publish it in your own
repository. For larger changes to an existing blueprint, please open an
[issue](https://github.com/mxstzdev/ha-blueprints/issues/new/choose) first so
we can agree on the approach before you spend time on it.

## Repository layout

```text
blueprints/<name>/      blueprint YAML, README.md, CHANGELOG.md (one folder per blueprint)
tests/                  pytest suite for all blueprints (shared harness in conftest.py)
tests/config/           example configuration validated with check_config
scripts/                validate.sh, check-config.sh, prepare-test-config.sh, resolve_ha_version.py,
                        create-blueprint.sh (maintainers)
.github/                CI, release, labels, issue forms, PR template, Dependabot
```

## Blueprint conventions

- **English only**, in the blueprint, the README and all comments.
- **Top-level docblock** in every file: what it does, how it works, and its
  requirements. Blueprints also carry a link to their folder and a
  `# Version: x.y.z # x-release-please-version` line (updated by releases).
- **Developer comments** wherever template logic is not obvious.
- **User-friendly inputs**: every input has a plain-language name and
  description, grouped into sections for larger blueprints.
- **User-friendly README** per blueprint: purpose, features, requirements,
  installation, step-by-step setup, options, FAQ. No developer details there;
  they belong in this file.
- **Requirements**: list every third-party integration (HACS) or other
  blueprint a blueprint depends on, in its README.
- **Log level**: larger blueprints offer a `log_level` input (Off, Info,
  Debug; default Info) that writes decisions to the logbook with
  `logbook.log`, using the automation's own entity, so users see them in the
  automation's activity without configuring a logger.
- `source_url` points at the file in this repository, so **Re-import
  blueprint** works.

## Running the checks locally

You need the Python version required by the current Home Assistant release
(3.14 at the time of writing).

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt
./scripts/validate.sh
```

| Check | What it does |
| --- | --- |
| `yamllint --strict` | YAML style and syntax |
| `ruff` | Lint and format check of the Python tests |
| `shellcheck` | Lint of the shell scripts in `scripts/` |
| `pytest` | Loads every blueprint into a real Home Assistant core (via `pytest-homeassistant-custom-component`) with mocked external services and asserts its behaviour |
| `scripts/check-config.sh` | Runs Home Assistant's `check_config` on [`tests/config`](tests/config/configuration.yaml) and fails on any error (it only logs invalid blueprint instances, so the output is scanned); `HA_TAG=stable` or `HA_TAG=beta` uses the official container |

Optional: `pip install pre-commit && pre-commit install` runs the linters
before every commit.

## Continuous integration

| Workflow | When | What |
| --- | --- | --- |
| [CI](.github/workflows/ci.yaml) | Push to main, pull requests, weekly | Lint, tests and `check_config` against the latest **stable** and **beta** Home Assistant. Versions and the required Python are resolved from PyPI on every run ([`resolve_ha_version.py`](scripts/resolve_ha_version.py)); beta jobs warn but don't block |
| [Release](.github/workflows/release.yaml) | Push to main | [release-please](https://github.com/googleapis/release-please) keeps a release PR per changed blueprint: version bump, `Version:` line, `CHANGELOG.md`. Merging it tags `<blueprint>-v<version>` and attaches the YAML files to the GitHub release |
| [PR title](.github/workflows/pr-title.yaml) | Pull requests | PR titles must be [Conventional Commits](https://www.conventionalcommits.org/) |
| [Labels](.github/workflows/labels.yaml) | Issues, pull requests | Adds `blueprint: <name>` labels from the issue form answer and from changed folders |
| [Dependabot](.github/dependabot.yml) | Weekly | Updates the GitHub Actions used above |

## Pull requests and releases

Pull requests are squash-merged, so the **PR title** becomes the commit that
release-please reads. Use Conventional Commits with the blueprint folder as
scope:

| Title | Effect |
| --- | --- |
| `fix(standby-mode): resume media after stop` | Patch release of Standby Mode |
| `feat(trash-reminder): add days-ahead option` | Minor release of Trash Reminder |
| `feat(courier)!: rename channel values` | Major release (breaking change) |
| `docs: ...`, `test: ...`, `ci: ...`, `chore: ...` | No release unless a blueprint folder changed |

Each blueprint is versioned on its own, based on the files changed in its
folder. Fill in the [pull request template](.github/pull_request_template.md)
checklist.

## Adding a blueprint (maintainers)

New blueprints are added by the maintainer only (see
[What contributions are welcome](#what-contributions-are-welcome)).
[`scripts/create-blueprint.sh`](scripts/create-blueprint.sh) creates the boilerplate. It is
a plain POSIX shell script, so it runs as it is on Linux, macOS and WSL:

```bash
./scripts/create-blueprint.sh window-open-alert \
  --name "Window Open Alert" \
  --description "Reminds you when a window stays open while the heating is on." \
  --log-level              # optional: off/info/debug log level for larger blueprints
# --domain script          # for a script blueprint (default: automation)
```

It creates `blueprints/<folder>/` with the blueprint YAML (docblock, version
marker, `source_url`, input sections), `README.md` and `CHANGELOG.md`, a test
in `tests/` and an instance in `tests/config/configuration.yaml`. It also
registers the folder in `release-please-config.json`, `.github/labeler.yml`,
both issue forms, the PR title scopes and the table in the [README](README.md).
The result passes `./scripts/validate.sh` as it is; fill in every `TODO`
before opening the pull request. Nothing is written if the folder exists or
an input is invalid.

## Shared interfaces

### Notification script interface

Notifications are sent by calling the selected script with `script.turn_on`
and these variables, so any script that accepts them can replace
[Courier](blueprints/courier/README.md):

| Variable | Description |
| --- | --- |
| `recipients` | Who gets it: a target (`{entity_id: [person...], label_id: [...]}`), a list or a comma-separated string of person entities, label IDs or names, or `all`. Empty means everyone |
| `title`, `message` | Text of the notification |
| `channel` | `default`, `auto`, `app`, `telegram` or `both` |
| `tag` | Identifies the notification so it can be replaced or cleared |
| `actions` | Buttons as `[{action: "TYPE&#124;target", title: "Label"}]` |
| `priority` | `normal` or `high` |
| `clear` | `true` removes the notification with `tag` |

Calling blueprints offer a "Who should be notified" input (target selector,
default `{}`) and pass it on unchanged as `recipients`.

### Button events (`courier_action`)

The Action Dispatcher fires one event for every button press, whether it came
from the Companion App or Telegram:

```yaml
event_type: courier_action
event_data:
  type: BAT_OK       # part before "|" of the button action
  target: abc123     # part after "|", may be empty
  source: app        # app | telegram
```

For Telegram it also answers the callback query and removes the inline
keyboard. Button actions must stay below 64 bytes (Telegram limit).

## Blueprint internals

### Courier: Notifications for People

#### Channel selection

`recipient_people` resolves the recipients to person entities (labels via
`label_entities`, `all` via the *People* input or every `person.*`). For each
person `deliveries` decides the channel: forced channel, else Telegram for
`priority: high` or when the person is not `home`, else the App; each with a
fallback to the other channel. People without any channel end up in
`unreachable` and are reported with `system_log.write`.

#### Phones and chats

- Phones: every entry of the person's `device_trackers` whose device has a
  `mobile_app` identifier. The notify action is
  `notify.mobile_app_<slugified device name>`, which is how the Companion App
  names it. *Companion App per person* overrides this.
- Telegram: the notify entity per allowed chat (config subentry) of the
  Telegram Bot integration. `telegram_bot.send_message` accepts these as
  `entity_id` since Home Assistant 2026.3, which sets the minimum version.

## Repository settings (maintainers)

- Allow **squash merging** only, with the PR title as commit message.
- Pull requests opened by release-please with the default `GITHUB_TOKEN` do
  not trigger CI. To run CI on release PRs, store a fine-grained token as a
  secret and pass it as `token:` to the release-please action.

## License

By contributing you agree that your contributions are licensed under the
[MIT License](LICENSE).
