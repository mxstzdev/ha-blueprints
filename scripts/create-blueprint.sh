#!/bin/sh
# Create the boilerplate for a new blueprint and register it in the repository.
#
# Usage:
#   ./scripts/create-blueprint.sh <folder-name> --name "Display name" \
#       --description "One sentence for users." [--domain automation|script] [--log-level]
#
# Creates blueprints/<folder-name>/ with the blueprint YAML, README.md and
# CHANGELOG.md, a test in tests/ and an instance in tests/config/configuration.yaml,
# then registers the folder everywhere the repository lists its blueprints:
# release-please, the PR labeler, both issue forms, the PR title scopes and the
# table in the root README. The generated files pass all checks as they are;
# every TODO marks a place to fill in.
#
# --log-level adds the "Debugging" input section with the off/info/debug log
# level, meant for larger blueprints.
#
# Portability: POSIX sh, sed, awk, fold and mktemp only (no GNU extensions such
# as `sed -i`), so it runs unchanged on Linux, macOS, the BSDs and WSL.
# Every change is prepared in a temporary directory first; if any check fails,
# the repository is left untouched.
set -eu

OWNER=mxstzdev
REPO=ha-blueprints
ROOT=${CREATE_BLUEPRINT_ROOT:-$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)}

usage() {
  sed -n '4,6s/^# \{0,1\}//p' "$0" >&2
  exit 2
}

fail() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

# --- Arguments ----------------------------------------------------------------

slug=''
name=''
description=''
domain=automation
log_level=false

while [ $# -gt 0 ]; do
  case $1 in
    --name) [ $# -ge 2 ] || usage; name=$2; shift 2 ;;
    --description) [ $# -ge 2 ] || usage; description=$2; shift 2 ;;
    --domain) [ $# -ge 2 ] || usage; domain=$2; shift 2 ;;
    --log-level) log_level=true; shift ;;
    -h | --help) usage ;;
    -*) printf 'error: unknown option %s\n' "$1" >&2; usage ;;
    *) [ -z "$slug" ] || usage; slug=$1; shift ;;
  esac
done

[ -n "$slug" ] && [ -n "$name" ] && [ -n "$description" ] || usage

newline='
'
case $slug in
  # Explicit letters instead of a-z: ranges can include uppercase in some locales.
  -* | *- | *--* | *[!abcdefghijklmnopqrstuvwxyz0123456789-]*) fail "'$slug' is not a valid folder name: use lowercase letters, digits and dashes" ;;
esac
case $domain in
  automation | script) ;;
  *) fail "--domain must be automation or script" ;;
esac
# The name ends up in YAML strings, Jinja literals and a Markdown table; the description in the table.
case $name in
  *[\"\'\|\\]* | *"$newline"*) fail "--name must not contain quotes, pipes, backslashes or line breaks" ;;
esac
case $description in
  *[\|\\]* | *"$newline"*) fail "--description must not contain pipes, backslashes or line breaks" ;;
esac

file=$(printf '%s' "$slug" | tr '-' '_')
folder="blueprints/$slug"
test_file="tests/test_$file.py"
url="https://github.com/$OWNER/$REPO/blob/main/blueprints/$slug/$file.yaml"
encoded=$(printf '%s' "$url" | sed -e 's|:|%3A|g' -e 's|/|%2F|g')
badge="[![Import blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=$encoded)"

[ ! -e "$ROOT/$folder" ] || fail "$folder already exists"
[ ! -e "$ROOT/$test_file" ] || fail "$test_file already exists"

edited="README.md release-please-config.json .github/labeler.yml .github/workflows/pr-title.yaml tests/config/configuration.yaml"
issue_forms=''
for form in "$ROOT"/.github/ISSUE_TEMPLATE/*.yml; do
  if [ -f "$form" ] && grep -q 'Which blueprint?' "$form"; then
    issue_forms="$issue_forms .github/ISSUE_TEMPLATE/${form##*/}"
  fi
done
[ -n "$issue_forms" ] || fail ".github/ISSUE_TEMPLATE: no issue form with a 'Which blueprint?' dropdown"
for relative in $edited; do
  [ -f "$ROOT/$relative" ] || fail "$relative not found"
done

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT INT TERM

# --- Helpers ------------------------------------------------------------------

# Escape a value for the replacement side of `sed s|...|...|`.
sed_escape() {
  printf '%s' "$1" | sed -e 's/[&|\\]/\\&/g'
}

# Replace the @PLACEHOLDERS@ of a template read from stdin.
fill() {
  sed -e "s|@OWNER@|$OWNER|g" \
    -e "s|@REPO@|$REPO|g" \
    -e "s|@SLUG@|$slug|g" \
    -e "s|@FILE@|$file|g" \
    -e "s|@DOMAIN@|$domain|g" \
    -e "s|@NAME@|$(sed_escape "$name")|g" \
    -e "s|@DESCRIPTION@|$(sed_escape "$description")|g" \
    -e "s|@BADGE@|$(sed_escape "$badge")|g"
}

# Insert stdin before the first line matching the awk regex $2 in file $1 (in $work).
insert_before() {
  target=$1 pattern=$2
  cat > "$work/insert"
  awk -v pattern="$pattern" -v insert="$work/insert" '
    !done && $0 ~ pattern { while ((getline line < insert) > 0) print line; done = 1 }
    { print }
    END { if (!done) exit 3 }
  ' "$work/$target" > "$work/tmp" || fail "$target: could not find a line matching $pattern"
  mv "$work/tmp" "$work/$target"
}

# --- Blueprint YAML -----------------------------------------------------------

blueprint_yaml() {
  fill <<'EOF'
# =============================================================================
# @NAME@ (@DOMAIN@ blueprint)
# https://github.com/@OWNER@/@REPO@/tree/main/blueprints/@SLUG@
# Version: 1.0.0 # x-release-please-version
# -----------------------------------------------------------------------------
# TODO: Describe what the blueprint does and which integrations it relies on.
#
# Flow
#   TODO: Describe the triggers, conditions and actions step by step.
# =============================================================================
blueprint:
  name: "@NAME@"
  description: >-
EOF
  printf '%s\n' "$description" | fold -s -w 80 | sed -e 's/ *$//' -e 's/^/    /'
  fill <<'EOF'
  domain: @DOMAIN@
  # yamllint disable-line rule:line-length
  source_url: https://github.com/@OWNER@/@REPO@/blob/main/blueprints/@SLUG@/@FILE@.yaml
  homeassistant:
    min_version: "2024.10.0"
  input:
    general:
      name: General
      icon: mdi:cog-outline
      input:
        # TODO: Replace with the inputs this blueprint needs.
EOF
  if [ "$domain" = automation ]; then
    cat <<'EOF'
        trigger_entity:
          name: Trigger entity
          description: "The entity whose changes start this automation."
          selector:
            entity:
EOF
  else
    fill <<'EOF'
        prefix:
          name: Prefix
          description: "Text written in front of every message."
          default: "@NAME@"
          selector:
            text:
EOF
  fi
  if $log_level; then
    cat <<'EOF'
    debugging:
      name: Debugging
      icon: mdi:bug-outline
      collapsed: true
      input:
        log_level:
          name: Log level
          description: >-
            "Info" writes every decision to the logbook (automation → Activity),
            "Debug" adds trigger and state details, "Off" writes nothing.
          default: info
          selector:
            select:
              options:
                - label: "Off"
                  value: "off"
                - label: Info
                  value: info
                - label: Debug
                  value: debug
EOF
  fi

  if [ "$domain" = automation ]; then
    cat <<'EOF'

mode: queued
max: 10

triggers:
  - trigger: state
    entity_id: !input trigger_entity

variables:
EOF
  else
    cat <<'EOF'

fields:
  message:
    name: Message
    description: The text to write to the logbook.
    required: true
    selector:
      text:

mode: queued
max: 10

variables:
  prefix: !input prefix
EOF
  fi
  if $log_level; then
    cat <<'EOF'
  log_level: !input log_level
  log_info: "{{ log_level in ['info', 'debug'] }}"
  log_debug: "{{ log_level == 'debug' }}"
EOF
  fi
  fill <<'EOF'
  log_name: "{{ state_attr(this.entity_id, 'friendly_name') or '@NAME@' }}"

EOF

  if [ "$domain" = automation ]; then
    printf 'actions:\n'
    message='      {{ trigger.entity_id }} changed to
      {{ trigger.to_state.state if trigger.to_state else '"'unknown'"' }}.'
  else
    printf 'sequence:\n'
    message='      {{ prefix }}: {{ message }}'
  fi
  printf '  # TODO: Replace with the blueprint'"'"'s actions.\n'
  indent='  '
  if $log_level; then
    printf '  - if: "{{ log_info }}"\n    then:\n'
    indent='      '
  fi
  sed "s/^/$indent/" <<EOF
- action: logbook.log
  data:
    name: "{{ log_name }}"
    entity_id: "{{ this.entity_id }}"
    message: >-
$message
EOF
}

# --- README and CHANGELOG -----------------------------------------------------

readme() {
  fill <<'EOF'
# @NAME@

[![CI](https://github.com/@OWNER@/@REPO@/actions/workflows/ci.yaml/badge.svg)](https://github.com/@OWNER@/@REPO@/actions/workflows/ci.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)

Part of [@REPO@](../../README.md). [Changelog](CHANGELOG.md) ·
[Report a problem](https://github.com/@OWNER@/@REPO@/issues/new/choose)

@DESCRIPTION@

TODO: Explain in two or three sentences, for non-developers, what this
blueprint does for them.

## Features

- TODO: One line per feature

## Requirements

| What | Type | Why it is needed |
| --- | --- | --- |
| Home Assistant 2024.10 or newer | Core | Blueprint syntax used here |

*Core* means it ships with Home Assistant. *HACS* means a community
integration you install through [HACS](https://hacs.xyz/). *Blueprint* means
another blueprint from this collection.

## Installation

**Easiest way:** click the button and confirm in Home Assistant.

@BADGE@

**Manual way:** download [`@FILE@.yaml`](@FILE@.yaml) and copy it to
`config/blueprints/@DOMAIN@/@OWNER@/` on your Home Assistant. Then go to
**Developer tools → YAML** and click **Automations** (or **Scripts**) under
*YAML configuration reloading*, or simply restart Home Assistant.

Updates: open **Settings → Automations & scenes → Blueprints**, click the
blueprint's **⋮** menu and choose **Re-import blueprint**. The version is shown
in the `Version:` line at the top of the blueprint file and in the
[changelog](CHANGELOG.md).

## Setup, step by step

1. Go to **Settings → Automations & scenes → Blueprints** and click
   **@NAME@**.
2. TODO: Describe each field the user has to fill in.
3. Save. That's it.

## Options

| Option | Default | What it does |
| --- | --- | --- |
| TODO | TODO | TODO |

EOF
  if $log_level; then
    fill <<'EOF'
## Seeing what it does (log level)

Every decision can be written to the Home Assistant **logbook**, so you can
check why something happened (or did not happen) without any extra setup.

| Log level | What you see |
| --- | --- |
| **Info** (default) | One line per decision |
| **Debug** | Additionally the details behind each decision, marked `[debug]` |
| **Off** | Nothing |

Change it under **Debugging** when editing the @DOMAIN@.

Where to find the entries: open the @DOMAIN@ and click **⋮ → Information**
to see its activity, or open **Activity** (called **Logbook** in older
versions) in the sidebar and filter for the @DOMAIN@.

Even more detail: **⋮ → Traces** in the @DOMAIN@ editor shows every step of
each run.

EOF
  fi
  fill <<'EOF'
## FAQ

**TODO: A question users will ask.** TODO: The answer.

## Help and feedback

EOF
  if $log_level; then
    printf 'Something not working as expected? Set the **Log level** to **Debug**, then\n'
  else
    printf 'Something not working as expected?\n'
  fi
  fill <<'EOF'
[open an issue](https://github.com/@OWNER@/@REPO@/issues/new/choose) and pick
this blueprint. Want to change the blueprint yourself? See
[CONTRIBUTING.md](../../CONTRIBUTING.md).

## License

MIT License, see the [LICENSE](../../LICENSE) file.
EOF
}

changelog() {
  cat <<'EOF'
# Changelog

All notable changes to this blueprint are documented here. This file is
maintained by [release-please](https://github.com/googleapis/release-please)
from the Conventional Commits that touch this folder.
EOF
}

# --- Test module --------------------------------------------------------------

test_module() {
  if [ "$domain" = automation ]; then
    fill <<'EOF'
"""@NAME@.

TODO: List the behaviour covered here.
"""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import async_mock_service

from .conftest import setup_automation


async def test_logs_the_trigger(blueprint_hass) -> None:
    log = async_mock_service(blueprint_hass, "logbook", "log")
    blueprint_hass.states.async_set("input_boolean.example", "off")
    inputs = {"trigger_entity": "input_boolean.example"}
    await setup_automation(blueprint_hass, "@FILE@", inputs)

    blueprint_hass.states.async_set("input_boolean.example", "on")
    await blueprint_hass.async_block_till_done()

    assert len(log) == 1
    assert log[0].data["message"] == "input_boolean.example changed to on."
EOF
    $log_level || return 0
    fill <<'EOF'


async def test_log_level_off_writes_nothing(blueprint_hass) -> None:
    log = async_mock_service(blueprint_hass, "logbook", "log")
    blueprint_hass.states.async_set("input_boolean.example", "off")
    inputs = {"trigger_entity": "input_boolean.example", "log_level": "off"}
    await setup_automation(blueprint_hass, "@FILE@", inputs)

    blueprint_hass.states.async_set("input_boolean.example", "on")
    await blueprint_hass.async_block_till_done()

    assert log == []
EOF
  else
    fill <<'EOF'
"""@NAME@.

TODO: List the behaviour covered here.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_mock_service

from .conftest import NAMESPACE


async def setup_script(hass: HomeAssistant, **inputs: Any) -> None:
    """Create `script.@FILE@` from the blueprint."""
    blueprint = {"path": f"{NAMESPACE}/@FILE@.yaml", "input": inputs}
    assert await async_setup_component(hass, "script", {"script": {"@FILE@": {"use_blueprint": blueprint}}})


async def test_logs_the_message(blueprint_hass) -> None:
    log = async_mock_service(blueprint_hass, "logbook", "log")
    await setup_script(blueprint_hass, prefix="Test")

    await blueprint_hass.services.async_call("script", "@FILE@", {"message": "hello"}, blocking=True)

    assert len(log) == 1
    assert log[0].data["message"] == "Test: hello"
EOF
    $log_level || return 0
    fill <<'EOF'


async def test_log_level_off_writes_nothing(blueprint_hass) -> None:
    log = async_mock_service(blueprint_hass, "logbook", "log")
    await setup_script(blueprint_hass, log_level="off")

    await blueprint_hass.services.async_call("script", "@FILE@", {"message": "hello"}, blocking=True)

    assert log == []
EOF
  fi
}

# --- Prepare every change in $work --------------------------------------------

mkdir -p "$work/$folder" "$work/tests"
blueprint_yaml > "$work/$folder/$file.yaml"
readme > "$work/$folder/README.md"
changelog > "$work/$folder/CHANGELOG.md"
test_module > "$work/$test_file"

for relative in $edited $issue_forms; do
  mkdir -p "$work/$(dirname "$relative")"
  cp "$ROOT/$relative" "$work/$relative"
done

# Example instance validated by check_config.
if [ "$domain" = automation ]; then
  fill <<'EOF' >> "$work/tests/config/configuration.yaml"

  - id: @FILE@
    alias: "@NAME@"
    use_blueprint:
      path: @OWNER@/@FILE@.yaml
      input:
        trigger_entity: input_boolean.example
EOF
else
  fill <<'EOF' | insert_before tests/config/configuration.yaml '^automation:'
  @FILE@:
    use_blueprint:
      path: @OWNER@/@FILE@.yaml
      input:
        prefix: "@NAME@"

EOF
fi

# release-please: append a package after the last one, or fill an empty `"packages": {}`.
awk -v slug="$slug" -v file="$file" '
  function package() {
    printf "    \"blueprints/%s\": {\n", slug
    printf "      \"component\": \"%s\",\n", slug
    printf "      \"extra-files\": [\"%s.yaml\"]\n", file
    print "    }"
  }
  { lines[NR] = $0 }
  END {
    for (i = 1; i <= NR; i++) if (lines[i] == "  \"packages\": {}") break
    if (i <= NR) {
      for (j = 1; j < i; j++) print lines[j]
      print "  \"packages\": {"
      package()
      print "  }"
      for (j = i + 1; j <= NR; j++) print lines[j]
      exit 0
    }
    for (i = NR; i > 1; i--) if (lines[i] == "  }" && lines[i - 1] == "    }") break
    if (i == 1) exit 3
    for (j = 1; j < i - 1; j++) print lines[j]
    print "    },"
    package()
    for (j = i; j <= NR; j++) print lines[j]
  }
' "$work/release-please-config.json" > "$work/tmp" ||
  fail "release-please-config.json: could not find the end of \"packages\""
mv "$work/tmp" "$work/release-please-config.json"

fill <<'EOF' | insert_before .github/labeler.yml '^"ci":'
"blueprint: @SLUG@":
  - changed-files:
      - any-glob-to-any-file: blueprints/@SLUG@/**
EOF

for form in $issue_forms; do
  fill <<'EOF' | insert_before "$form" '^ *- Other / not specific to one blueprint'
        - @NAME@ (@SLUG@)
EOF
done

printf '            %s\n' "$slug" | insert_before .github/workflows/pr-title.yaml '^ +repo$'

# Root README: add a row at the end of the table between the blueprints markers.
printf '| [%s](blueprints/%s/README.md) | %s | %s |\n' "$name" "$slug" "$description" "$badge" |
  insert_before README.md '^<!-- blueprints:end -->'

# --- Write everything ---------------------------------------------------------

printf 'Created and updated:\n'

for relative in "$folder/$file.yaml" "$folder/README.md" "$folder/CHANGELOG.md" "$test_file" $edited $issue_forms; do
  mkdir -p "$ROOT/$(dirname "$relative")"
  cp "$work/$relative" "$ROOT/$relative"
  printf '  %s\n' "$relative"
done
printf '\nNext: fill in every TODO, then run ./scripts/validate.sh.\n'
