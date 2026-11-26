"""Deterministic trigger policy: chance, cooldown, skips, forced replies."""

import pytest

from gamoaicog.trigger import TriggerResult, cooldown_remaining, is_command_like, should_reply

BASE = {
    "is_bot": False,
    "is_webhook": False,
    "is_dm": False,
    "is_nsfw": False,
    "channel_allowed": True,
    "ai_enabled": True,
}


def test_command_prefix_is_never_treated_as_chatter():
    prefixes = ["!", "?"]
    assert is_command_like("!gamoai status", prefixes)
    assert is_command_like("  ?help", prefixes)
    assert not is_command_like("hola !gamoai status", prefixes)
    assert not is_command_like("gamoai status", prefixes)
    assert not is_command_like("", prefixes)
    assert not is_command_like("hola", [])


def test_default_chance_is_twenty_percent_and_zero_chance_never_draws():
    assert should_reply(**BASE, rng=lambda: 0.1) == TriggerResult(True, "random")
    assert should_reply(**BASE, rng=lambda: 0.3) == TriggerResult(False, "random")

    def explode():
        raise AssertionError("rng must not be consulted at 0% chance")

    assert should_reply(**BASE, chance=0.0, rng=explode) == TriggerResult(False, "chance-zero")


def test_random_draw_is_strictly_below_chance():
    assert should_reply(**BASE, chance=0.25, rng=lambda: 0.24) == TriggerResult(True, "random")
    assert should_reply(**BASE, chance=0.25, rng=lambda: 0.25) == TriggerResult(False, "random")
    assert should_reply(**BASE, chance=1.0, rng=lambda: 0.999) == TriggerResult(True, "random")


@pytest.mark.parametrize(
    ("last_reply_at", "now", "cooldown", "expected"),
    [
        (None, 100.0, 30.0, 0.0),
        (100.0, 100.0, 30.0, 30.0),
        (100.0, 110.0, 30.0, 20.0),
        (100.0, 130.0, 30.0, 0.0),
        (100.0, 200.0, 30.0, 0.0),
        (100.0, 110.0, 0.0, 0.0),
        (100.0, 110.0, -5.0, 0.0),
    ],
)
def test_cooldown_remaining_math(last_reply_at, now, cooldown, expected):
    assert cooldown_remaining(last_reply_at, now, cooldown) == expected


@pytest.mark.parametrize(("flag", "reason"), [("is_mention", "mention"), ("is_reply", "reply")])
def test_mentions_and_replies_always_reply_and_bypass_cooldown_and_chance(flag, reason):
    result = should_reply(
        **BASE,
        **{flag: True},
        remaining=999.0,
        chance=0.0,
        rng=lambda: 1.0,
    )
    assert result == TriggerResult(True, reason)


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"is_bot": True}, "automated"),
        ({"is_webhook": True}, "automated"),
        ({"is_dm": True}, "dm"),
        ({"is_nsfw": True}, "nsfw"),
        ({"channel_allowed": False}, "channel-not-allowed"),
        ({"blocked_topic": True}, "blocked-topic"),
        ({"ai_enabled": False}, "ai-disabled"),
    ],
)
def test_blocked_sources_channels_and_topics_are_skipped(overrides, reason):
    options = {**BASE, **overrides}
    assert should_reply(**options, is_mention=True, is_reply=True) == TriggerResult(False, reason)


def test_cooldown_blocks_only_non_forced_turns():
    assert should_reply(**BASE, remaining=0.5, chance=1.0, rng=lambda: 0.0) == TriggerResult(
        False, "cooldown"
    )
