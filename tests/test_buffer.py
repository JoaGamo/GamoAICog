"""Per-channel locks, passive buffering, flush thresholds and idle detection."""

import asyncio

from gamoaicog.buffer import ChannelManager
from gamoaicog.models import ChatMessage


class FakeClock:
    """Injectable monotonic clock: never sleeps, only advances on demand."""

    def __init__(self, value=0.0):
        self.value = value

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


def message(message_id, channel_id=7):
    return ChatMessage(
        guild_id=1,
        channel_id=channel_id,
        author_id=42,
        author_name="tester",
        text=f"message-{message_id}",
        message_id=message_id,
    )


def test_lock_identity_is_per_channel():
    manager = ChannelManager(clock=FakeClock())
    lock = manager.lock(7)

    assert isinstance(lock, asyncio.Lock)
    assert manager.lock(7) is lock
    assert manager.get(7).lock is lock
    assert manager.lock(8) is not lock


def test_buffer_flushes_at_fifteen_messages():
    manager = ChannelManager(clock=FakeClock())

    for message_id in range(14):
        assert manager.add(7, message(message_id)) is False
    assert manager.add(7, message(14)) is True

    batch = manager.drain(7)
    assert [item.message_id for item in batch] == list(range(15))
    assert manager.drain(7) == []
    assert manager.buffered_counts() == {}


def test_buffer_flushes_after_180_seconds_idle_with_injected_clock():
    clock = FakeClock(1000.0)
    manager = ChannelManager(clock=clock)

    manager.add(7, message(1))
    clock.value = 1179.0
    assert manager.idle_channels() == []

    clock.value = 1180.0
    assert manager.idle_channels() == [7]

    batch = manager.drain(7)
    assert [item.message_id for item in batch] == [1]
    assert manager.idle_channels() == []


def test_idle_detection_uses_per_channel_activity_and_explicit_now():
    clock = FakeClock(0.0)
    manager = ChannelManager(clock=clock)

    manager.add(7, message(1))  # activity at t=0
    clock.value = 100.0
    manager.add(8, message(2, channel_id=8))  # activity at t=100

    assert manager.idle_channels(now=279.0) == [7]
    assert manager.idle_channels(now=280.0) == [7, 8]


def test_drop_message_removes_only_the_deleted_message():
    manager = ChannelManager(clock=FakeClock())
    for message_id in range(3):
        manager.add(7, message(message_id))

    assert manager.drop_message(7, 1) is True
    assert [item.message_id for item in manager.drain(7)] == [0, 2]


def test_drop_message_ignores_unknown_message_or_channel():
    manager = ChannelManager(clock=FakeClock())
    manager.add(7, message(1))

    assert manager.drop_message(7, 999) is False
    assert manager.drop_message(99, 1) is False
    assert [item.message_id for item in manager.drain(7)] == [1]


def test_manager_cooldown_uses_injected_clock_and_mark_reply():
    clock = FakeClock(10.0)
    manager = ChannelManager(clock=clock)

    assert manager.cooldown_remaining(7, 30.0) == 0.0
    clock.value = 15.0
    manager.mark_reply(7)
    clock.value = 25.0
    assert manager.cooldown_remaining(7, 30.0) == 20.0
    clock.value = 45.0
    assert manager.cooldown_remaining(7, 30.0) == 0.0
