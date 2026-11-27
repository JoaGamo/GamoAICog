"""Opt-in live test against a disposable Hindsight bank.

Run with a real key and URL in the environment:

    GAMOAI_INTEGRATION=1 HINDSIGHT_API_KEY=... pytest -m integration

Retain is async: Hindsight queues the operation and processes it whenever it
can. The test verifies the retain is accepted and the bank is purgeable.
Recall is polled best-effort and reported, never required to be immediate.
The test bank is deleted in teardown; it never touches gamoaibot-user-* or
gamoaibot-guild-* banks.
"""

from __future__ import annotations

import os
import time
import uuid

import aiohttp
import pytest

from gamoaicog.constants import test_bank as make_test_bank
from gamoaicog.hindsight import HindsightClient, memory_item

pytestmark = pytest.mark.integration


@pytest.fixture
async def client():
    if os.getenv("GAMOAI_INTEGRATION") != "1":
        pytest.skip("set GAMOAI_INTEGRATION=1 to run live Hindsight tests")
    api_key = os.getenv("HINDSIGHT_API_KEY", "")
    if not api_key:
        pytest.skip("HINDSIGHT_API_KEY is not set")
    base_url = os.getenv("HINDSIGHT_API_URL", "http://localhost:8888")
    async with aiohttp.ClientSession() as session:
        yield HindsightClient(base_url, api_key, 30.0, session)


async def test_async_retain_is_accepted_and_bank_is_purgeable(client: HindsightClient) -> None:
    bank = make_test_bank(uuid.uuid4().hex[:12])
    token = f"gamoai-roundtrip-{uuid.uuid4().hex[:8]}"
    tags = ["guild:999888777", "channel:111222333", "source:passive"]
    started = time.monotonic()
    found = False
    try:
        # Returns once Hindsight has queued the operation, not once it finished.
        await client.retain(
            bank,
            [memory_item(f"Dato de prueba: {token}", tags=tags, context="integration test")],
        )
        # Best-effort only: consolidation is server-scheduled.
        results = await client.recall(bank, token, tags=tags, budget="mid", limit=5)
        found = any(token in item["text"] for item in results)
    finally:
        purged = await client.purge(bank)

    elapsed = time.monotonic() - started
    print(
        f"async retain accepted in {elapsed:.1f}s; "
        f"recall {'found' if found else 'still pending (server processes async)'}"
    )
    assert purged
