#!/usr/bin/env bash
# Local equivalent of the CI pipeline: lint, unit tests and check_config.
# Usage: ./scripts/validate.sh             (check_config via Docker if available, else the venv)
#        HA_TAG=beta ./scripts/validate.sh  (check_config against the beta image)
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

yamllint --strict .
ruff check .
ruff format --check .
shellcheck scripts/*.sh
pytest

# Container image when Docker is available, otherwise the homeassistant package from the venv.
if [[ -z "${HA_TAG:-}" ]] && command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  export HA_TAG=stable
fi
./scripts/check-config.sh
