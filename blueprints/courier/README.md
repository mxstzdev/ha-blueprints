# Courier: Notifications for People

[![CI](https://github.com/mxstzdev/ha-blueprints/actions/workflows/ci.yaml/badge.svg)](https://github.com/mxstzdev/ha-blueprints/actions/workflows/ci.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)

Part of [ha-blueprints](../../README.md). [Changelog](CHANGELOG.md) ·
[Report a problem](https://github.com/mxstzdev/ha-blueprints/issues/new/choose)

Send notifications to **people** instead of phones. Courier knows who is at
home: at home you get the message in the Home Assistant app, on the go via
**Telegram**. Send to one person, to a group like *parents* or *kids*, or to
everyone, with buttons that work the same in the app and in Telegram.

## Features

- Send to people, to groups (Home Assistant labels such as `parents` or
  `kids`) or to everyone
- At home: Home Assistant app. Away: Telegram. Courier picks per person
- Important alerts go to Telegram first, because it works everywhere
- Finds each person's phones automatically from their person settings
- Buttons ("actionable notifications") that work in the app **and** in Telegram
- Replace or remove an earlier notification using a tag
- Telegram chat IDs stay in the Telegram integration, not in the blueprint
- If one phone is offline, the others still get the message

This folder contains **two blueprints that belong together**:

| Blueprint | What it is | Import |
| --- | --- | --- |
| Courier: Notifications for People | The script that sends notifications | [![Import script blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fmxstzdev%2Fha-blueprints%2Fblob%2Fmain%2Fblueprints%2Fcourier%2Fcourier.yaml) |
| Courier: Action Dispatcher | An automation that handles button presses | [![Import automation blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fmxstzdev%2Fha-blueprints%2Fblob%2Fmain%2Fblueprints%2Fcourier%2Fcourier_action_dispatcher.yaml) |

## Requirements

| What | Type | Why it is needed |
| --- | --- | --- |
| Home Assistant 2026.3 or newer | Core | Sending to the Telegram chat entities needs this version |
| [People](https://www.home-assistant.io/integrations/person/) | Core | Courier sends to people and checks who is at home |
| [Home Assistant Companion App](https://companion.home-assistant.io/) | Core | Notifications on your phone (optional if you only use Telegram) |
| [Telegram Bot](https://www.home-assistant.io/integrations/telegram_bot/) | Core | Messages via Telegram (optional if you only use the app). You need a bot from @BotFather |

*Core* means it ships with Home Assistant. *HACS* means a community
integration you install through [HACS](https://hacs.xyz/). *Blueprint* means
another blueprint from this collection.

Each person needs at least one of the two channels.

## Installation

Click both buttons in the table above and confirm in Home Assistant.

**Manual way:** copy [`courier.yaml`](courier.yaml) to
`config/blueprints/script/mxstzdev/` and
[`courier_action_dispatcher.yaml`](courier_action_dispatcher.yaml) to
`config/blueprints/automation/mxstzdev/`, then restart Home Assistant (or
reload **Scripts** and **Automations** under **Developer tools → YAML**).

## Setup, step by step

1. **Check your people.** Go to **Settings → People**. For each person, pick
   their phone under **Track devices**. Courier uses it to find the phone and
   to know whether the person is at home.
2. **Add groups (optional).** Go to **Settings → Labels**, create labels like
   `Parents` or `Kids` and add them to the person entities (**Settings →
   Entities**, open the person, ⚙️ → **Labels**).
3. **(Telegram only) Allow the chats.** Set up the
   [Telegram Bot](https://www.home-assistant.io/integrations/telegram_bot/)
   and add one allowed chat per person. Each chat gets an entity such as
   `notify.telegram_bot_marius` (see **Settings → Entities**, search
   `notify.telegram`).
4. **Create the script.** Go to **Settings → Automations & scenes →
   Blueprints** and click **Courier: Notifications for People**. Under
   *Telegram chat per person* add one line per person, for example
   `person.marius: notify.telegram_bot_marius`. Name the script **courier** so
   other blueprints find it as `script.courier`.
5. **Create the dispatcher.** Click **Courier: Action Dispatcher**, keep the
   defaults and save. Create it **only once**.
6. **Test it.** Go to **Developer tools → Actions**, choose `script.courier`,
   pick a person, enter a message and click **Perform action**.

## How Courier picks the channel

| Situation | Channel |
| --- | --- |
| Person is at home | Home Assistant app (Telegram if the person has no phone) |
| Person is away | Telegram (app if the person has no Telegram chat) |
| High priority | Telegram (app if the person has no Telegram chat) |
| Channel set to App, Telegram or both | That channel, for everyone |

If a person has neither a phone nor a Telegram chat, Courier writes a warning
to the Home Assistant log (**Settings → System → Logs**).

## Options

**Script**

| Option | Default | What it does |
| --- | --- | --- |
| People | empty | Who "everyone" means. Empty uses every person in Home Assistant |
| Telegram chat per person | empty | Lines like `person.marius: notify.telegram_bot_marius`. People without a line only get app notifications |
| Companion App per person | empty | Only if the wrong phone is picked: `person.marius: notify.mobile_app_pixel_8` |
| Default channel | Automatic | Used whenever an automation does not pick a channel |

**Dispatcher**

| Option | Default | What it does |
| --- | --- | --- |
| Allowed action types | empty (all) | Limit which buttons are handled, e.g. `BAT_OK`, `OFF_ACK`, `OFF_RELOAD` |
| Telegram confirmation text | ✔ Done | Short message shown in Telegram after a button press |

## Using it in your own automations

Send a notification:

```yaml
action: script.turn_on
target:
  entity_id: script.courier
data:
  variables:
    recipients:             # optional, empty means everyone
      label_id: parents     # a label, or entity_id: person.marius
    title: "Washing machine"
    message: "Laundry is done."
    channel: default        # default | auto | app | telegram | both
    tag: washing_machine    # optional: replace or clear it later
    priority: normal        # normal | high
    actions:                # optional buttons
      - action: "LAUNDRY_OK|washer"
        title: "Emptied"
```

Remove it again from every phone of the recipients (Companion App only):

```yaml
action: script.turn_on
target:
  entity_id: script.courier
data:
  variables:
    recipients:
      label_id: parents
    message: clear
    tag: washing_machine
    clear: true
```

React to a button press, no matter if it came from the App or Telegram:

```yaml
triggers:
  - trigger: event
    event_type: courier_action
    event_data:
      type: LAUNDRY_OK
```

## FAQ

**Nothing arrives on my phone.** Check that the phone is picked under **Track
devices** of the person (step 1) and that the Companion App may show
notifications. If the wrong phone is used, add a line under *Companion App per
person*. Warnings about people Courier cannot reach are in **Settings → System
→ Logs**.

**I am at home but got a Telegram message.** Either the message was sent with
high priority, or Home Assistant does not see you at home yet. Check the state
of your person entity.

**Where do I find the Telegram chat entities?** Each allowed chat of the
Telegram Bot integration has an entity. Go to **Settings → Entities** and
search for `notify.telegram`.

**Telegram buttons do nothing.** The Action Dispatcher automation must exist
and be enabled. In Telegram the buttons disappear after one press, which is
intended.

**Can I clear Telegram messages?** No, clearing works for the Companion App
only.

## Limitations

- Button IDs (`TYPE|target`) must stay below 64 characters (Telegram limit).
- Button labels must not contain commas.

## Help and feedback

Something not working as expected? Look at **⋮ → Traces** in the script
editor, then
[open an issue](https://github.com/mxstzdev/ha-blueprints/issues/new/choose) and pick
this blueprint. Want to change the blueprint yourself? See
[CONTRIBUTING.md](../../CONTRIBUTING.md).

## License

MIT License, see the [LICENSE](../../LICENSE) file.
