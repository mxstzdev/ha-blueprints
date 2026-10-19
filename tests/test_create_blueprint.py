"""Scaffold script (scripts/create-blueprint.sh).

Runs the script against a copy of the repository files it edits and checks the
generated files, every registration, that the generated blueprints load and run
in Home Assistant, that invalid input leaves the repository untouched, and that
every POSIX shell installed here produces the same result.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_mock_service

from .conftest import NAMESPACE, setup_automation

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "create-blueprint.sh"
SHELLS = [shell for shell in ("sh", "dash", "bash", "ksh", "zsh", "busybox") if shutil.which(shell)]
EDITED = [
    "README.md",
    "release-please-config.json",
    ".github/labeler.yml",
    ".github/workflows/pr-title.yaml",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    "tests/config/configuration.yaml",
]


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A copy of the files the scaffold reads and edits."""
    root = tmp_path / "repo"
    for relative in EDITED:
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / relative, root / relative)
    (root / "blueprints").mkdir()
    return root


def snapshot(root: Path) -> dict[str, str]:
    return {str(path.relative_to(root)): path.read_text() for path in root.rglob("*") if path.is_file()}


def run(root: Path, slug: str, *extra: str, name: str = "Window Open Alert", shell: str = "sh") -> int:
    """Run the scaffold on `root` and return its exit code."""
    command = [shell, *(["sh"] if shell == "busybox" else []), str(SCRIPT), slug, "--name", name]
    command += ["--description", "Tells you about open windows.", *extra]
    env = {**os.environ, "CREATE_BLUEPRINT_ROOT": str(root)}
    return subprocess.run(command, env=env, capture_output=True, check=False).returncode


@pytest.mark.parametrize("shell", SHELLS)
def test_same_result_in_every_shell(tmp_path: Path, shell: str) -> None:
    results = []
    for target in (tmp_path / "baseline", tmp_path / shell):
        for relative in EDITED:
            (target / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(REPO / relative, target / relative)
        assert run(target, "window-open-alert", "--log-level", shell="sh" if target.name == "baseline" else shell) == 0
        results.append(snapshot(target))
    assert results[0] == results[1]


def test_creates_files_and_registers_the_blueprint(repo: Path) -> None:
    assert run(repo, "window-open-alert", "--log-level") == 0

    folder = repo / "blueprints" / "window-open-alert"
    assert sorted(path.name for path in folder.iterdir()) == ["CHANGELOG.md", "README.md", "window_open_alert.yaml"]
    blueprint = (folder / "window_open_alert.yaml").read_text()
    assert "# Version: 1.0.0 # x-release-please-version" in blueprint
    assert "blob/main/blueprints/window-open-alert/window_open_alert.yaml" in blueprint
    assert "log_level:" in blueprint
    assert "## Seeing what it does (log level)" in (folder / "README.md").read_text()
    assert (repo / "tests" / "test_window_open_alert.py").exists()

    packages = json.loads((repo / "release-please-config.json").read_text())["packages"]
    assert packages["blueprints/window-open-alert"] == {
        "component": "window-open-alert",
        "extra-files": ["window_open_alert.yaml"],
    }
    assert '"blueprint: window-open-alert":' in (repo / ".github/labeler.yml").read_text()
    assert "            window-open-alert\n            repo\n" in (repo / ".github/workflows/pr-title.yaml").read_text()
    for form in ("bug_report.yml", "feature_request.yml"):
        text = (repo / ".github/ISSUE_TEMPLATE" / form).read_text()
        assert "- Window Open Alert (window-open-alert)\n        - Other / not specific" in text
    readme = (repo / "README.md").read_text()
    assert "| [Window Open Alert](blueprints/window-open-alert/README.md) | Tells you about open windows. |" in readme
    assert "path: mxstzdev/window_open_alert.yaml" in (repo / "tests/config/configuration.yaml").read_text()


def test_without_log_level(repo: Path) -> None:
    assert run(repo, "window-open-alert") == 0

    folder = repo / "blueprints" / "window-open-alert"
    assert "log_level" not in (folder / "window_open_alert.yaml").read_text()
    assert "log level" not in (folder / "README.md").read_text()


def test_script_is_added_to_the_script_section(repo: Path) -> None:
    assert run(repo, "say-hello", "--domain", "script", name="Say Hello") == 0

    config = (repo / "tests/config/configuration.yaml").read_text()
    assert config.index("  say_hello:") < config.index("\nautomation:")
    assert "domain: script" in (repo / "blueprints/say-hello/say_hello.yaml").read_text()


@pytest.mark.parametrize(
    ("slug", "name"),
    [
        ("Window_Open", "Window Open Alert"),  # invalid folder name
        ("window-open-alert", "Window's Alert"),  # quote in the name
        ("courier", "Courier"),  # folder already exists
    ],
)
def test_invalid_input_changes_nothing(repo: Path, slug: str, name: str) -> None:
    (repo / "blueprints" / "courier").mkdir()
    before = snapshot(repo)

    assert run(repo, slug, name=name) == 1
    assert snapshot(repo) == before


def test_missing_anchor_changes_nothing(repo: Path) -> None:
    labeler = repo / ".github/labeler.yml"
    labeler.write_text(labeler.read_text().replace('"ci":', '"other":'))
    before = snapshot(repo)

    assert run(repo, "window-open-alert") == 1
    assert snapshot(repo) == before


async def install(hass: HomeAssistant, repo: Path, domain: str, file: str) -> None:
    target = Path(hass.config.config_dir) / "blueprints" / domain / NAMESPACE
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy(repo / "blueprints" / file.replace("_", "-") / f"{file}.yaml", target / f"{file}.yaml")


@pytest.mark.parametrize("log_level", [True, False])
async def test_generated_automation_runs(blueprint_hass: HomeAssistant, repo: Path, log_level: bool) -> None:
    run(repo, "window-open-alert", *(["--log-level"] if log_level else []))
    await install(blueprint_hass, repo, "automation", "window_open_alert")
    log = async_mock_service(blueprint_hass, "logbook", "log")
    blueprint_hass.states.async_set("input_boolean.window", "off")
    await setup_automation(blueprint_hass, "window_open_alert", {"trigger_entity": "input_boolean.window"})

    blueprint_hass.states.async_set("input_boolean.window", "on")
    await blueprint_hass.async_block_till_done()

    assert [call.data["message"] for call in log] == ["input_boolean.window changed to on."]


@pytest.mark.parametrize("log_level", [True, False])
async def test_generated_script_runs(blueprint_hass: HomeAssistant, repo: Path, log_level: bool) -> None:
    run(repo, "say-hello", "--domain", "script", *(["--log-level"] if log_level else []), name="Say Hello")
    await install(blueprint_hass, repo, "script", "say_hello")
    log = async_mock_service(blueprint_hass, "logbook", "log")
    blueprint = {"path": f"{NAMESPACE}/say_hello.yaml", "input": {}}
    assert await async_setup_component(
        blueprint_hass, "script", {"script": {"say_hello": {"use_blueprint": blueprint}}}
    )

    await blueprint_hass.services.async_call("script", "say_hello", {"message": "hi"}, blocking=True)

    assert [call.data["message"] for call in log] == ["Say Hello: hi"]
