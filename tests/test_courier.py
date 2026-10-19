"""Courier script and Action Dispatcher automation.

Covers resolving recipients (people, labels, everyone), choosing the channel per
person (home, away, high priority, forced channel, fallbacks), finding the phones
of a person through their mobile_app device trackers, the App and Telegram
payloads built from one button list, clearing by tag, unreachable recipients,
and how the dispatcher turns App actions and Telegram callbacks into
`courier_action` events.
"""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr
from homeassistant.util import slugify
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events, async_mock_service

from .conftest import NOTIFY_SCRIPT, setup_automation, setup_courier

BUTTONS = [
    {"action": "BAT_OK|dev1", "title": "Battery replaced"},
    {"action": "OFF_ACK|sensor.x", "title": "Acknowledge"},
]
TELEGRAM_CHATS = [
    "person.marius: notify.telegram_bot_marius",
    "person.anna: notify.telegram_bot_anna",
]


def add_phone(hass: HomeAssistant, name: str) -> str:
    """Register a Companion App phone and return its device tracker entity id."""
    entry = MockConfigEntry(domain="mobile_app", title=name)
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("mobile_app", name)}, name=name
    )
    tracker = er.async_get(hass).async_get_or_create(
        "device_tracker", "mobile_app", name, device_id=device.id, config_entry=entry, suggested_object_id=slugify(name)
    )
    return tracker.entity_id


def add_person(hass: HomeAssistant, name: str, state: str, trackers: list[str], labels: list[str]) -> None:
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get_or_create("person", "person", name, suggested_object_id=name)
    label_registry = lr.async_get(hass)
    label_ids = set()
    for label in labels:
        existing = label_registry.async_get_label_by_name(label)
        label_ids.add((existing or label_registry.async_create(label)).label_id)
    entity_registry.async_update_entity(entry.entity_id, labels=label_ids)
    hass.states.async_set(entry.entity_id, state, {"device_trackers": trackers})


@pytest.fixture
def family(blueprint_hass: HomeAssistant) -> dict[str, list[ServiceCall]]:
    """Marius (home, Pixel 8, Telegram), Anna (away, iPhone, Telegram), Kid (home, nothing)."""
    hass = blueprint_hass
    router_tracker = "device_tracker.router_marius"  # not a mobile_app tracker: ignored
    add_person(hass, "marius", "home", [add_phone(hass, "Pixel 8"), router_tracker], ["Parents"])
    add_person(hass, "anna", "not_home", [add_phone(hass, "Anna iPhone")], ["Parents"])
    add_person(hass, "kid", "home", [], ["Kids"])
    return {
        "pixel": async_mock_service(hass, "notify", "mobile_app_pixel_8"),
        "iphone": async_mock_service(hass, "notify", "mobile_app_anna_iphone"),
        "override": async_mock_service(hass, "notify", "mobile_app_tablet"),
        "telegram": async_mock_service(hass, "telegram_bot", "send_message"),
        "log": async_mock_service(hass, "system_log", "write"),
    }


async def courier(hass: HomeAssistant, **variables: Any) -> None:
    await hass.services.async_call("script", "courier", variables, blocking=True)
    await hass.async_block_till_done()


def telegram_targets(calls: list[ServiceCall]) -> list[list[str]]:
    return [call.data["entity_id"] for call in calls]


async def test_home_gets_app_away_gets_telegram(blueprint_hass, family) -> None:
    await setup_courier(blueprint_hass, telegram_chats=TELEGRAM_CHATS)

    await courier(blueprint_hass, recipients=["person.marius", "person.anna"], title="Hi", message="Hello")

    assert len(family["pixel"]) == 1
    app = family["pixel"][0].data
    assert app == {"title": "Hi", "message": "Hello", "data": {}}
    assert family["iphone"] == []
    assert telegram_targets(family["telegram"]) == [["notify.telegram_bot_anna"]]
    assert family["telegram"][0].data["title"] == "Hi"
    assert "inline_keyboard" not in family["telegram"][0].data


async def test_buttons_and_tag_on_both_channels(blueprint_hass, family) -> None:
    await setup_courier(blueprint_hass, telegram_chats=TELEGRAM_CHATS)

    await courier(blueprint_hass, recipients={"label_id": ["parents"]}, message="Hello", tag="t1", actions=BUTTONS)

    app = family["pixel"][0].data
    assert app["data"] == {"tag": "t1", "actions": BUTTONS}
    telegram = family["telegram"][0].data
    assert telegram["entity_id"] == ["notify.telegram_bot_anna"]
    assert telegram["inline_keyboard"] == ["Battery replaced:/BAT_OK|dev1, Acknowledge:/OFF_ACK|sensor.x"]
    assert "title" not in telegram


async def test_high_priority_prefers_telegram(blueprint_hass, family) -> None:
    await setup_courier(blueprint_hass, telegram_chats=["person.anna: notify.telegram_bot_anna"])

    await courier(blueprint_hass, recipients={"label_id": "parents"}, message="Water leak!", priority="high")

    # Marius is home but has no Telegram line: App with high-priority flags.
    assert family["pixel"][0].data["data"] == {
        "priority": "high",
        "ttl": 0,
        "push": {"interruption-level": "time-sensitive"},
    }
    assert telegram_targets(family["telegram"]) == [["notify.telegram_bot_anna"]]
    assert family["iphone"] == []


async def test_high_priority_at_home_goes_to_telegram(blueprint_hass, family) -> None:
    await setup_courier(blueprint_hass, telegram_chats=TELEGRAM_CHATS)

    await courier(blueprint_hass, recipients="person.marius", message="Water leak!", priority="high")

    assert family["pixel"] == []
    assert telegram_targets(family["telegram"]) == [["notify.telegram_bot_marius"]]


async def test_everyone_by_default(blueprint_hass, family) -> None:
    await setup_courier(blueprint_hass, telegram_chats=TELEGRAM_CHATS)

    await courier(blueprint_hass, message="Dinner is ready")

    assert len(family["pixel"]) == 1
    assert telegram_targets(family["telegram"]) == [["notify.telegram_bot_anna"]]
    # The kid has neither a phone nor a Telegram chat.
    assert "person.kid" in family["log"][0].data["message"]
    assert family["log"][0].data["level"] == "warning"


async def test_people_input_limits_everyone(blueprint_hass, family) -> None:
    await setup_courier(blueprint_hass, people=["person.marius"], telegram_chats=TELEGRAM_CHATS)

    await courier(blueprint_hass, recipients="all", message="Only Marius")

    assert len(family["pixel"]) == 1
    assert family["telegram"] == []
    assert family["log"] == []


async def test_label_by_name_and_unknown_label(blueprint_hass, family) -> None:
    await setup_courier(blueprint_hass, telegram_chats=TELEGRAM_CHATS)

    await courier(blueprint_hass, recipients="Parents, nobody", message="Hi parents")

    assert len(family["pixel"]) == 1
    assert telegram_targets(family["telegram"]) == [["notify.telegram_bot_anna"]]


@pytest.mark.parametrize(
    ("channel", "app_calls", "telegram"),
    [
        ("app", 1, []),
        ("telegram", 0, [["notify.telegram_bot_marius"]]),
        ("both", 1, [["notify.telegram_bot_marius"]]),
    ],
)
async def test_forced_channel(blueprint_hass, family, channel, app_calls, telegram) -> None:
    await setup_courier(blueprint_hass, telegram_chats=TELEGRAM_CHATS)

    await courier(blueprint_hass, recipients="person.marius", message="Forced", channel=channel)

    assert len(family["pixel"]) == app_calls
    assert telegram_targets(family["telegram"]) == telegram


async def test_default_channel_input(blueprint_hass, family) -> None:
    await setup_courier(blueprint_hass, telegram_chats=TELEGRAM_CHATS, default_channel="telegram")

    await courier(blueprint_hass, recipients="person.marius", message="Default is Telegram")
    await courier(blueprint_hass, recipients="person.marius", message="Explicit auto", channel="auto")

    assert telegram_targets(family["telegram"]) == [["notify.telegram_bot_marius"]]
    assert [call.data["message"] for call in family["pixel"]] == ["Explicit auto"]


async def test_away_without_telegram_falls_back_to_app(blueprint_hass, family) -> None:
    await setup_courier(blueprint_hass)

    await courier(blueprint_hass, recipients="person.anna", message="No Telegram")

    assert len(family["iphone"]) == 1
    assert family["telegram"] == []


async def test_app_override(blueprint_hass, family) -> None:
    await setup_courier(blueprint_hass, app_overrides=["person.marius: notify.mobile_app_tablet"])

    await courier(blueprint_hass, recipients="person.marius", message="On the tablet")

    assert len(family["override"]) == 1
    assert family["pixel"] == []


async def test_clear_reaches_every_phone(blueprint_hass, family) -> None:
    await setup_courier(blueprint_hass, telegram_chats=TELEGRAM_CHATS)

    await courier(blueprint_hass, recipients="parents", message="clear", tag="t1", clear=True)

    expected = {"message": "clear_notification", "data": {"tag": "t1"}}
    assert [call.data for call in family["pixel"]] == [expected]
    assert [call.data for call in family["iphone"]] == [expected]
    assert family["telegram"] == []


async def test_dispatcher_app_action(blueprint_hass) -> None:
    answer = async_mock_service(blueprint_hass, "telegram_bot", "answer_callback_query")
    await setup_automation(blueprint_hass, "courier_action_dispatcher", {})
    events = async_capture_events(blueprint_hass, "courier_action")

    blueprint_hass.bus.async_fire("mobile_app_notification_action", {"action": "BAT_OK|dev1"})
    await blueprint_hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data == {"type": "BAT_OK", "target": "dev1", "source": "app"}
    assert answer == []


async def test_dispatcher_telegram_callback(blueprint_hass) -> None:
    answer = async_mock_service(blueprint_hass, "telegram_bot", "answer_callback_query")
    edit = async_mock_service(blueprint_hass, "telegram_bot", "edit_replymarkup")
    await setup_automation(blueprint_hass, "courier_action_dispatcher", {})
    events = async_capture_events(blueprint_hass, "courier_action")

    blueprint_hass.bus.async_fire(
        "telegram_callback",
        {"id": "cb1", "data": "/OFF_ACK|sensor.fridge", "chat_id": 123456, "message": {"message_id": 42}},
    )
    await blueprint_hass.async_block_till_done()

    assert events[0].data == {"type": "OFF_ACK", "target": "sensor.fridge", "source": "telegram"}
    assert answer[0].data["callback_query_id"] == "cb1"
    assert edit[0].data == {"message_id": 42, "chat_id": 123456, "inline_keyboard": []}


async def test_dispatcher_allowed_types(blueprint_hass) -> None:
    await setup_automation(blueprint_hass, "courier_action_dispatcher", {"allowed_types": ["BAT_OK"]})
    events = async_capture_events(blueprint_hass, "courier_action")

    blueprint_hass.bus.async_fire("mobile_app_notification_action", {"action": "SOMETHING_ELSE"})
    blueprint_hass.bus.async_fire("mobile_app_notification_action", {"action": "BAT_OK|dev1"})
    await blueprint_hass.async_block_till_done()

    assert [event.data["type"] for event in events] == ["BAT_OK"]


async def test_courier_script_entity_exists(blueprint_hass) -> None:
    await setup_courier(blueprint_hass)
    assert blueprint_hass.states.get(NOTIFY_SCRIPT) is not None
