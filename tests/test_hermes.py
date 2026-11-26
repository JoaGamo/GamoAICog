"""Hermes chat wire format, channel-scoped sessions, inline images and errors."""

import asyncio

import pytest
from aioresponses import aioresponses

from gamoaicog.hermes import HermesClient, HermesError, session_ids
from gamoaicog.models import MediaAttachment

ENDPOINT = "http://hermes.test/v1"
CHAT_URL = f"{ENDPOINT}/chat/completions"


def recorded(mocked):
    return [
        request
        for (_, url), calls in mocked.requests.items()
        if str(url) == CHAT_URL
        for request in calls
    ]


def test_session_ids_are_channel_scoped():
    assert session_ids(1, 2) == ("discord-1-2", "discord:1:2")
    assert session_ids(1, 2) != session_ids(1, 3)
    assert session_ids(1, 2) != session_ids(2, 2)


def test_chat_posts_to_completions_with_auth_and_session_headers():
    async def run():
        client = HermesClient(ENDPOINT, "hermes-secret", model="gamoaibot")
        messages = [{"role": "user", "content": "hi"}]
        async with client:
            with aioresponses() as mocked:
                mocked.post(CHAT_URL, payload={"choices": [{"message": {"content": "  hello  "}}]})
                assert await client.chat(messages, guild_id=1, channel_id=2) == "hello"

                calls = recorded(mocked)
                assert len(calls) == 1
                headers = calls[0].kwargs["headers"]
                assert headers["Authorization"] == "Bearer hermes-secret"
                assert headers["X-Hermes-Session-Id"] == "discord-1-2"
                assert headers["X-Hermes-Session-Key"] == "discord:1:2"
                assert calls[0].kwargs["json"] == {
                    "model": "gamoaibot",
                    "messages": messages,
                    "stream": False,
                }

    asyncio.run(run())


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"choices": []},
        {"choices": [{}]},
        {"choices": [{"message": {}}]},
    ],
)
def test_chat_raises_clean_error_when_choices_are_missing(payload):
    async def run():
        client = HermesClient(ENDPOINT, "hermes-secret")
        async with client:
            with aioresponses() as mocked:
                mocked.post(CHAT_URL, payload=payload)
                with pytest.raises(HermesError, match="Hermes returned no choices\[0\].message.content"):
                    await client.chat([], guild_id=1, channel_id=2)

    asyncio.run(run())


def test_build_messages_inlines_image_url_data_urls():
    image_part = MediaAttachment(
        url="https://images.test/a.png",
        mime="image/png",
        filename="a.png",
        data_b64="QUJD",
    ).as_image_part()

    assert image_part == {"type": "image_url", "image_url": {"url": "data:image/png;base64,QUJD"}}
    assert HermesClient.build_messages("system", "[@tester|7] look", [image_part]) == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": [{"type": "text", "text": "[@tester|7] look"}, image_part]},
    ]


def test_build_messages_stays_plain_without_images():
    assert HermesClient.build_messages("system", "hello") == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "hello"},
    ]
