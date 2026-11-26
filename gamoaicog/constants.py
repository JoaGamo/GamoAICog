"""Bank IDs, tag vocabulary and topic guardrails.

All values here are derived from Discord IDs in the cog. Hermes templates are
deliberately not involved: the API server does not provide user_id/chat_id.
"""

from __future__ import annotations

import re

BANK_PREFIX = "gamoaibot"

SOURCE_REPLY = "source:reply"
SOURCE_PASSIVE = "source:passive"


def user_bank(guild_id: int, user_id: int) -> str:
    return f"{BANK_PREFIX}-user-{guild_id}-{user_id}"


def guild_bank(guild_id: int) -> str:
    return f"{BANK_PREFIX}-guild-{guild_id}"


def test_bank(suffix: str) -> str:
    return f"{BANK_PREFIX}-test-{suffix}"


def scope_tags(guild_id: int, channel_id: int, user_id: int | None, source: str) -> list[str]:
    """Flat, lowercase key:value tags.

    `user:` is omitted on multi-user passive batches: attaching one speaker to
    a batch of several people's messages would be a false attribution.
    """
    tags = [f"guild:{guild_id}", f"channel:{channel_id}"]
    if user_id is not None:
        tags.append(f"user:{user_id}")
    tags.append(source)
    return tags


# Conservative: block obvious political keyword spam and directly identifying
# strings. This is a guardrail, not a moderation system; false positives are
# cheaper than persisting private data into a memory bank.
_BLOCKED_PATTERNS = (
    re.compile(r"\b(eleccione?s|votos?|partido\s+pol[ií]tico|pol[ií]tica|campa[aã]n?a\s+pol[ií]tica)\b", re.I),
    re.compile(r"\b(president[ea]|senador|diputado|gobernador)\b", re.I),
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    re.compile(r"\b(?:\+?54\s?)?(?:\d[\s.-]?){10,13}\b"),
    re.compile(r"\b(?:\d[ -]?){13,19}\b"),
)


def is_blocked_topic(text: str) -> bool:
    return any(pattern.search(text or "") for pattern in _BLOCKED_PATTERNS)


def clean_text(text: str) -> str:
    """Drop control characters before text reaches a bank or an LLM."""
    return "".join(ch for ch in (text or "") if ch in "\n\t" or ord(ch) >= 32).strip()
