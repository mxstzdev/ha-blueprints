"""Shared test harness: load the blueprints into a real Home Assistant core instance.

The tests run against Home Assistant itself (pytest-homeassistant-custom-component),
so blueprint schemas, templates, triggers and the script engine are all exercised for
real. External services (phones, Telegram, Battery Notes, calendars, lights, ...) are
mock services that record their calls.

Every `blueprints/<name>/*.yaml` file is copied into the test config directory under
`blueprints/<domain>/mxstzdev/`, where `<domain>` (automation or script) is read from
the blueprint itself.

Two ways to observe notifications:
- `notify_calls` mocks `script.turn_on`, so feature blueprints can be tested without
  Courier; tests assert the variables handed to the notify script.
- `mock_notify` + `setup_courier` run the real Courier script and record what reaches
  the Companion App and Telegram.
"""

from __future__ import annotations

import re
import shutil
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_mock_service

BLUEPRINTS = Path(__file__).resolve().parent.parent / "blueprints"
NAMESPACE = "mxstzdev"
DOMAIN_LINE = re.compile(r"^  domain: (automation|script)$", re.M)

NOTIFY_SCRIPT = "script.courier"
APP_SERVICE = "notify.mobile_app_test_phone"
TELEGRAM_ENTITY = "notify.telegram_bot_marius"


def blueprint_domain(path: Path) -> str:
    """Return `automation` or `script` as declared in the blueprint metadata."""
    match = DOMAIN_LINE.search(path.read_text())
    assert match, f"{path} has no blueprint domain"
    return match.group(1)


@pytest.fixture
async def blueprint_hass(hass: HomeAssistant, tmp_path: Path) -> AsyncGenerator[HomeAssistant]:
    """Home Assistant with all blueprints of this repository in its config dir."""
    hass.config.config_dir = str(tmp_path)
    for source in BLUEPRINTS.glob("*/*.yaml"):
        target = tmp_path / "blueprints" / blueprint_domain(source) / NAMESPACE
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, target / source.name)
    yield hass
    # Detach triggers and stop waiting runs, so no timers linger after the test.
    if hass.services.has_service("automation", "turn_off"):
        await hass.services.async_call(
            "automation", "turn_off", {"entity_id": "all", "stop_actions": True}, blocking=True
        )


@pytest.fixture
def notify_calls(blueprint_hass: HomeAssistant) -> list[ServiceCall]:
    """Record calls to `script.turn_on` (the Courier script)."""
    return async_mock_service(blueprint_hass, "script", "turn_on")


def notifications(calls: list[ServiceCall]) -> list[dict[str, Any]]:
    """Variables passed to the notify script, one dict per call."""
    for call in calls:
        assert call.data["entity_id"] == [NOTIFY_SCRIPT]
    return [dict(call.data["variables"]) for call in calls]


@pytest.fixture
def mock_notify(blueprint_hass: HomeAssistant) -> dict[str, list[ServiceCall]]:
    """Record Companion App and Telegram calls made by the real Courier script."""
    domain, service = APP_SERVICE.split(".")
    return {
        "app": async_mock_service(blueprint_hass, domain, service),
        "telegram": async_mock_service(blueprint_hass, "telegram_bot", "send_message"),
        "answer_callback": async_mock_service(blueprint_hass, "telegram_bot", "answer_callback_query"),
        "edit_markup": async_mock_service(blueprint_hass, "telegram_bot", "edit_replymarkup"),
    }


async def setup_courier(hass: HomeAssistant, **inputs: Any) -> None:
    """Create `script.courier` from the Courier blueprint."""
    blueprint = {"path": f"{NAMESPACE}/courier.yaml", "input": inputs}
    assert await async_setup_component(hass, "script", {"script": {"courier": {"use_blueprint": blueprint}}})


async def setup_automation(hass: HomeAssistant, blueprint: str, inputs: dict[str, Any]) -> None:
    """Create `automation.<blueprint>` from `<blueprint>.yaml`."""
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "id": blueprint,
                "alias": blueprint,
                "use_blueprint": {"path": f"{NAMESPACE}/{blueprint}.yaml", "input": inputs},
            }
        },
    )
    await hass.async_block_till_done()
