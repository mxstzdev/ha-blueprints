#!/usr/bin/env bash
# Validates tests/config with Home Assistant's check_config and fails on any error.
#
# check_config only logs invalid automations and scripts generated from
# blueprints (its exit code stays 0), so the output is scanned as well.
#
# Usage: ./scripts/check-config.sh                 (homeassistant from the active venv)
#        HA_TAG=stable ./scripts/check-config.sh   (official container image)
#        HA_TAG=beta ./scripts/check-config.sh
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bash "$root/scripts/prepare-test-config.sh"

if [[ -n "${HA_TAG:-}" ]]; then
  cmd=(docker run --rm -v "$root/tests/config:/config"
    "ghcr.io/home-assistant/home-assistant:${HA_TAG}"
    python -m homeassistant --script check_config --config /config)
else
  cmd=(python -m homeassistant --script check_config --config "$root/tests/config")
fi

if ! output="$("${cmd[@]}" 2>&1)"; then
  echo "$output"
  exit 1
fi
echo "$output"

if grep -qE "ERROR|Invalid config|Failed config" <<<"$output"; then
  echo "check_config reported errors" >&2
  exit 1
fi
echo "check_config: configuration valid"
