"""Opt-in round-trip test against a disposable Hindsight bank.

Run only with a real key and URL in the environment:

    GAMOAI_INTEGRATION=1 HINDSIGHT_API_KEY=... pytest -m integration

The test bank is created by retain and deleted in teardown. It never touches
a gamoaibot-user-* or gamoaibot-guild-* bank.
"""

from __future__ import annotations

import asyncio
import os
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
    base_url = os.getenv("HINDSIGHT_API_URL", "http://<INTERNAL_HOST>:8888")
    async with aiohttp.ClientSession() as session:
        yield HindsightClient(base_url, api_key, 30.0, session)


async def test_retain_recall_purge_roundtrip(client: HindsightClient) -> None:
    bank = make_test_bank(uuid.uuid4().hex[:12])
    token = f"gamoai-roundtrip-{uuid.uuid4().hex[:8]}"
    tags = ["guild:999888777", "channel:111222333", "source:passive"]
    try:
        await client.retain(
            bank,
            [memory_item(f"Dato de prueba: {token}", tags=tags, context="integration test")],
        )
        results: list[dict] = []
        for _ in range(10):
            results = await client.recall(bank, token, tags=tags, budget="mid", limit=5)
            if any(token in item["text"] for item in results):
                break
            await asyncio.sleep(0.5)
        assert any(token in item["text"] for item in results)
        formatted = HindsightClient.format_context(results, "Memoria")
        assert token in formatted
    finally:
        await client.purge(bank)
