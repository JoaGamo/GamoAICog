"""Hindsight retain/recall wire format, response parsing and context rendering."""

import asyncio

from aioresponses import aioresponses

from gamoaicog.hindsight import HindsightClient, memory_item

BASE = "http://hindsight.test"
BANK = "gamoaibot-guild-7"
MEMORIES_URL = f"{BASE}/v1/default/banks/{BANK}/memories"
RECALL_URL = f"{BASE}/v1/default/banks/{BANK}/memories/recall"


def recorded(mocked, method, url):
    return [
        request
        for (verb, request_url), calls in mocked.requests.items()
        if verb == method and str(request_url) == url
        for request in calls
    ]


def test_retain_posts_items_with_async_false():
    async def run():
        client = HindsightClient(BASE, "hindsight-secret", session=None)
        items = [
            memory_item("hello", tags=["guild:7", "source:passive"]),
            memory_item("world", tags=["guild:7"], document_id="doc-1", context="ctx"),
        ]
        async with client:
            with aioresponses() as mocked:
                mocked.post(MEMORIES_URL, payload={})
                await client.retain(BANK, items)

                calls = recorded(mocked, "POST", MEMORIES_URL)
                assert len(calls) == 1
                assert calls[0].kwargs["json"] == {"items": items, "async": False}
                assert calls[0].kwargs["headers"]["Authorization"] == "Bearer hindsight-secret"

    asyncio.run(run())


def test_retain_with_no_items_makes_no_request():
    async def run():
        client = HindsightClient(BASE, "hindsight-secret")
        async with client:
            with aioresponses() as mocked:
                await client.retain(BANK, [])
                assert recorded(mocked, "POST", MEMORIES_URL) == []

    asyncio.run(run())


def test_recall_posts_query_budget_and_tags_and_parses_results():
    async def run():
        client = HindsightClient(BASE, "hindsight-secret")
        payload = {
            "results": [
                {"text": "first", "type": "fact", "context": "ctx", "tags": ["guild:7"]},
                {"text": "", "type": "fact"},
                {"text": "second"},
                {"text": "third"},
            ]
        }
        async with client:
            with aioresponses() as mocked:
                mocked.post(RECALL_URL, payload=payload)
                results = await client.recall(BANK, "what happened", tags=["guild:7"], budget="mid", limit=3)

                assert results == [
                    {"text": "first", "type": "fact", "context": "ctx", "tags": ["guild:7"]},
                    {"text": "second", "type": None, "context": None, "tags": []},
                ]
                calls = recorded(mocked, "POST", RECALL_URL)
                assert len(calls) == 1
                assert calls[0].kwargs["json"] == {
                    "query": "what happened",
                    "budget": "mid",
                    "tags": ["guild:7"],
                    "tags_match": "any",
                }

    asyncio.run(run())


def test_recall_honors_the_result_limit():
    async def run():
        client = HindsightClient(BASE, "hindsight-secret")
        payload = {"results": [{"text": text} for text in ("one", "two", "three")]}
        async with client:
            with aioresponses() as mocked:
                mocked.post(RECALL_URL, payload=payload)
                results = await client.recall(BANK, "hello", limit=1)
                assert results == [{"text": "one", "type": None, "context": None, "tags": []}]

    asyncio.run(run())


def test_recall_omits_tag_filters_when_none_are_given():
    async def run():
        client = HindsightClient(BASE, "hindsight-secret")
        async with client:
            with aioresponses() as mocked:
                mocked.post(RECALL_URL, payload={"results": []})
                assert await client.recall(BANK, "hello") == []
                assert recorded(mocked, "POST", RECALL_URL)[0].kwargs["json"] == {
                    "query": "hello",
                    "budget": "mid",
                }

    asyncio.run(run())


def test_format_context_renders_label_text_and_optional_context():
    assert HindsightClient.format_context([], "self-memory") == ""
    assert HindsightClient.format_context(
        [
            {"text": "remembered", "context": "guild:7"},
            {"text": "plain"},
        ],
        "self-memory",
    ) == "[self-memory]\n- remembered (guild:7)\n- plain"
