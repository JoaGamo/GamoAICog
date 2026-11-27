"""Bank identity and the flat key:value tag vocabulary."""

import pytest

from gamoaicog import constants
from gamoaicog.constants import (
    BANK_PREFIX,
    SOURCE_PASSIVE,
    SOURCE_REPLY,
    blocked_topic_reason,
    guild_bank,
    scope_tags,
    user_bank,
)


def test_bank_ids_are_derived_from_discord_ids():
    assert BANK_PREFIX == "gamoaibot"
    assert user_bank(123, 456) == "gamoaibot-user-123-456"
    assert guild_bank(123) == "gamoaibot-guild-123"
    assert constants.test_bank("smoke") == "gamoaibot-test-smoke"


@pytest.mark.parametrize(
    ("user_id", "source", "expected"),
    [
        (33, SOURCE_REPLY, ["guild:11", "channel:22", "user:33", "source:reply"]),
        (33, SOURCE_PASSIVE, ["guild:11", "channel:22", "user:33", "source:passive"]),
        (None, SOURCE_PASSIVE, ["guild:11", "channel:22", "source:passive"]),
    ],
)
def test_scope_tags_are_flat_lowercase_pairs(user_id, source, expected):
    tags = scope_tags(11, 22, user_id, source)
    assert tags == expected
    assert all(tag == tag.lower() and tag.count(":") == 1 for tag in tags)


def test_multi_user_passive_batches_omit_the_user_tag():
    assert SOURCE_REPLY == "source:reply"
    assert SOURCE_PASSIVE == "source:passive"
    assert scope_tags(11, 22, None, SOURCE_PASSIVE) == ["guild:11", "channel:22", "source:passive"]


BOT_ID = 894230173103292456


@pytest.mark.parametrize(
    "text",
    [
        f"<@{BOT_ID}> hola",
        f"hola <@!{BOT_ID}> como va",
        f"<@{BOT_ID}> <@{BOT_ID}>",
    ],
)
def test_own_mention_is_not_a_blocked_topic(text):
    assert blocked_topic_reason(text, bot_id=BOT_ID) is None


@pytest.mark.parametrize(
    ("text", "bot_id", "reason"),
    [
        (f"<@{BOT_ID}> hola", None, "long_number"),
        ("<@111111111111111111> hola", BOT_ID, "long_number"),
        ("hola 1575943383145517056", BOT_ID, "long_number"),
        (f"<@{BOT_ID}> 1575943383145517056", BOT_ID, "long_number"),
        ("mi telefono es 1145678901", BOT_ID, "phone"),
        (f"<@{BOT_ID}> llamame al 1145678901", BOT_ID, "phone"),
        ("escribime a juan@example.com", BOT_ID, "email"),
        ("votaron en las elecciones", BOT_ID, "politics"),
    ],
)
def test_other_numbers_and_topics_still_block(text, bot_id, reason):
    assert blocked_topic_reason(text, bot_id=bot_id) == reason
