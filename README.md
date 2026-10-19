# Home Assistant Blueprints

[![CI](https://github.com/mxstzdev/ha-blueprints/actions/workflows/ci.yaml/badge.svg)](https://github.com/mxstzdev/ha-blueprints/actions/workflows/ci.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Ready-to-use [Home Assistant](https://www.home-assistant.io/) blueprints for
notifications and everyday automations. You set everything up in the Home
Assistant UI, no YAML needed.

## Available blueprints

<!-- blueprints:start: rows are added by scripts/create-blueprint.sh -->
| Blueprint | What it does | Install |
| --- | --- | --- |
| [Courier](blueprints/courier/README.md) | Sends notifications to people or groups like parents or kids: in the Home Assistant app at home, via Telegram on the go. Most other blueprints use it. | [![Import blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fmxstzdev%2Fha-blueprints%2Fblob%2Fmain%2Fblueprints%2Fcourier%2Fcourier.yaml) |
| [Courier: Action Dispatcher](blueprints/courier/README.md) | Makes notification buttons work. Add it once, together with Courier. | [![Import blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fmxstzdev%2Fha-blueprints%2Fblob%2Fmain%2Fblueprints%2Fcourier%2Fcourier_action_dispatcher.yaml) |
<!-- blueprints:end -->

Click **Import** next to a blueprint and confirm in Home Assistant. Then go to
**Settings → Automations & scenes → Blueprints**, click the blueprint and fill
in the form. Each blueprint's page (click its name) explains the setup step by
step and lists what else you need.

## Where to start

Most blueprints send their notifications through **Courier**, so
set that up first:

1. Import **Courier** and create a script from it named `courier`.
2. Import the **Action Dispatcher** and create one automation from it. It
   makes the buttons in notifications work.
3. Blueprints that send notifications ask for this script: choose
   `script.courier`.

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

These blueprints are free and open source under the MIT License. See the
[LICENSE](LICENSE) file for the full text.
