"""Per-channel concurrency and in-memory passive buffers.

No external queue: one asyncio.Lock per channel serializes Hermes turns, and
messages that did not trigger a reply are batched to Hindsight on count or idle.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable

from .models import ChatMessage


@dataclass
class ChannelState:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    buffered: list[ChatMessage] = field(default_factory=list)
    last_activity: float = 0.0
    last_reply_at: float | None = None


class ChannelManager:
    def __init__(
        self,
        flush_count: int = 15,
        idle_seconds: float = 180.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.flush_count = flush_count
        self.idle_seconds = idle_seconds
        self._clock = clock
        self._channels: dict[int, ChannelState] = {}

    def get(self, channel_id: int) -> ChannelState:
        return self._channels.setdefault(channel_id, ChannelState())

    def lock(self, channel_id: int) -> asyncio.Lock:
        return self.get(channel_id).lock

    def add(self, channel_id: int, message: ChatMessage) -> bool:
        """Buffer a message; True means the count threshold was reached.

        Callers must hold the channel lock. `drain()` then takes the batch.
        """
        state = self.get(channel_id)
        state.buffered.append(message)
        state.last_activity = self._clock()
        return len(state.buffered) >= self.flush_count

    def drain(self, channel_id: int) -> list[ChatMessage]:
        state = self.get(channel_id)
        batch, state.buffered = state.buffered, []
        return batch

    def idle_channels(self, now: float | None = None) -> list[int]:
        now = self._clock() if now is None else now
        return [
            channel_id
            for channel_id, state in self._channels.items()
            if state.buffered and now - state.last_activity >= self.idle_seconds
        ]

    def drop_message(self, channel_id: int, message_id: int) -> bool:
        state = self._channels.get(channel_id)
        if state is None:
            return False
        before = len(state.buffered)
        state.buffered = [m for m in state.buffered if m.message_id != message_id]
        return len(state.buffered) != before

    def mark_reply(self, channel_id: int, now: float | None = None) -> None:
        stamp = self._clock() if now is None else now
        self.get(channel_id).last_reply_at = stamp
        self.get(channel_id).last_activity = stamp

    def cooldown_remaining(self, channel_id: int, cooldown: float, now: float | None = None) -> float:
        now = self._clock() if now is None else now
        state = self._channels.get(channel_id)
        last = state.last_reply_at if state else None
        if last is None or cooldown <= 0:
            return 0.0
        return max(0.0, cooldown - (now - last))

    def buffered_counts(self) -> dict[int, int]:
        return {cid: len(state.buffered) for cid, state in self._channels.items() if state.buffered}

    def set_thresholds(self, flush_count: int, idle_seconds: float) -> None:
        self.flush_count = flush_count
        self.idle_seconds = idle_seconds
