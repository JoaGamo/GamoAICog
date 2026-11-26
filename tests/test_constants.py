"""Bank identity and the flat key:value tag vocabulary."""

import pytest

from gamoaicog import constants
from gamoaicog.constants import (
    BANK_PREFIX,
    SOURCE_PASSIVE,
    SOURCE_REPLY,
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
