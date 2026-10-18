# Home Assistant Blueprints

[![CI](https://github.com/mxstzdev/ha-blueprints/actions/workflows/ci.yaml/badge.svg)](https://github.com/mxstzdev/ha-blueprints/actions/workflows/ci.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Ready-to-use [Home Assistant](https://www.home-assistant.io/) blueprints for
notifications and everyday automations. You set everything up in the Home
Assistant UI, no YAML needed.

## Available blueprints

<!-- blueprints:start: rows are added by scripts/new-blueprint.sh -->
| Blueprint | What it does | Install |
| --- | --- | --- |
<!-- blueprints:end -->

Click **Import** next to a blueprint and confirm in Home Assistant. Then go to
**Settings → Automations & scenes → Blueprints**, click the blueprint and fill
in the form. Each blueprint's page (click its name) explains the setup step by
step and lists what else you need.

## Updating a blueprint

Go to **Settings → Automations & scenes → Blueprints**, click the **⋮** menu
next to the blueprint and choose **Re-import blueprint**. What changed is
listed in the blueprint's changelog (linked at the top of its page) and on the
[releases page](https://github.com/mxstzdev/ha-blueprints/releases).

## Help and issues

Something not working, or an idea for an improvement?

1. If something doesn't work and the blueprint has a **Log level** option,
   set it to **Debug** (in the automation, under **Debugging**) and let it
   run once more. The entries show up in the automation's activity.
2. [Open an issue](https://github.com/mxstzdev/ha-blueprints/issues/new/choose),
   choose **Bug report** or **Feature request** and pick the blueprint it is
   about.
3. Describe what you expected and what happened, and paste the logbook
   entries. Remove personal information first.

Before opening a new issue, have a look at the
[open issues](https://github.com/mxstzdev/ha-blueprints/issues); someone may
have reported it already.

Want to fix a bug or improve one of the blueprints yourself? Read
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

These blueprints are free and open source under the [MIT License](LICENSE).
