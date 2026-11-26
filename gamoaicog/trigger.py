"""Deterministic trigger policy. No Discord imports so it can be unit-tested."""

from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass


def is_command_like(text: str, prefixes: Iterable[str]) -> bool:
    """True when a message starts with one of the bot's command prefixes.

    Kept pure so the guardrail can be tested without Red. In the cog this is
    combined with `get_context()` so resolved commands are caught too.
    """
    stripped = (text or "").lstrip()
    return any(prefix and stripped.startswith(prefix) for prefix in prefixes)


@dataclass(frozen=True)
class TriggerResult:
    reply: bool
    reason: str


def cooldown_remaining(last_reply_at: float | None, now: float, cooldown: float) -> float:
    if last_reply_at is None or cooldown <= 0:
        return 0.0
    return max(0.0, cooldown - (now - last_reply_at))


def should_reply(
    *,
    is_bot: bool,
    is_webhook: bool,
    is_dm: bool,
    is_nsfw: bool,
    channel_allowed: bool,
    ai_enabled: bool,
    blocked_topic: bool = False,
    is_mention: bool = False,
    is_reply: bool = False,
    chance: float = 0.2,
    remaining: float = 0.0,
    rng=None,
) -> TriggerResult:
    """Decide one turn. `chance` is 0..1; `rng` is injectable for tests.

    Mentions and direct replies bypass the cooldown on purpose: "always reply"
    means always. Everything else is subject to it.
    """
    if is_bot or is_webhook:
        return TriggerResult(False, "automated")
    if is_dm:
        return TriggerResult(False, "dm")
    if is_nsfw:
        return TriggerResult(False, "nsfw")
    if not channel_allowed:
        return TriggerResult(False, "channel-not-allowed")
    if blocked_topic:
        return TriggerResult(False, "blocked-topic")
    if not ai_enabled:
        return TriggerResult(False, "ai-disabled")
    if is_mention:
        return TriggerResult(True, "mention")
    if is_reply:
        return TriggerResult(True, "reply")
    if remaining > 0:
        return TriggerResult(False, "cooldown")
    if chance <= 0:
        return TriggerResult(False, "chance-zero")
    draw = rng() if rng is not None else random.random()
    return TriggerResult(draw < chance, "random")
