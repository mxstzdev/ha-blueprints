#!/usr/bin/env bash
# Copies every blueprint into tests/config/blueprints/<domain>/mxstzdev/ so
# `check_config` (or a local Home Assistant pointed at tests/config) can load
# the example configuration. The domain (automation or script) is read from
# each blueprint's `domain:` line.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for blueprint in "$root"/blueprints/*/*.yaml; do
  [[ -e "$blueprint" ]] || continue  # no blueprints yet
  domain="$(sed -nE 's/^  domain: (automation|script)$/\1/p' "$blueprint" | head -n 1)"
  if [[ -z "$domain" ]]; then
    echo "No blueprint domain found in $blueprint" >&2
    exit 1
  fi
  target="$root/tests/config/blueprints/$domain/mxstzdev"
  mkdir -p "$target"
  cp "$blueprint" "$target/"
done
echo "Blueprints copied to tests/config/blueprints/*/mxstzdev"
