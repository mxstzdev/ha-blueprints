"""Resolve the Home Assistant version and Python version CI should test with.

Usage: python scripts/resolve_ha_version.py stable|beta

Prints `ha_version=<x>` and `python_version=<major.minor>` lines in the
GitHub Actions output format. The Python version is read from the release's
`requires_python`, so CI never silently falls back to an older Home Assistant
because the runner's Python is too old for the newest release.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request

PYPI = "https://pypi.org/pypi/homeassistant"
VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:b(\d+))?$")


def fetch(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def sort_key(version: str) -> tuple[int, int, int, int]:
    match = VERSION.match(version)
    assert match, version
    major, minor, patch, beta = match.groups()
    # A final release sorts after all of its betas.
    return int(major), int(minor), int(patch), int(beta) if beta is not None else 1_000


def resolve(channel: str) -> tuple[str, str]:
    info = fetch(f"{PYPI}/json")
    if channel == "stable":
        version = info["info"]["version"]
    elif channel == "beta":
        candidates = [v for v, files in info["releases"].items() if files and VERSION.match(v)]
        version = max(candidates, key=sort_key)
    else:
        raise SystemExit(f"unknown channel {channel!r}, expected stable or beta")

    requires = fetch(f"{PYPI}/{version}/json")["info"]["requires_python"] or ""
    match = re.search(r">=\s*(\d+)\.(\d+)", requires)
    if not match:
        raise SystemExit(f"cannot parse requires_python {requires!r} of homeassistant {version}")
    return version, f"{match.group(1)}.{match.group(2)}"


if __name__ == "__main__":
    ha_version, python_version = resolve(sys.argv[1] if len(sys.argv) > 1 else "stable")
    print(f"ha_version={ha_version}")
    print(f"python_version={python_version}")
