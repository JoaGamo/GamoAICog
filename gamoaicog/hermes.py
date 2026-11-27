"""Client for the gamoaibot profile's OpenAI-compatible API server."""

from __future__ import annotations

import aiohttp


class HermesError(RuntimeError):
    pass


def session_ids(guild_id: int, channel_id: int) -> tuple[str, str]:
    """Channel-scoped session ID and stable key.

    Per-user IDs would split one visible channel conversation into separate
    transcripts; bank identity is handled independently by the cog.
    """
    return (
        f"discord-{guild_id}-{channel_id}",
        f"discord:{guild_id}:{channel_id}",
    )


class HermesClient:
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        model: str = "gamoaibot",
        timeout: float = 120.0,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._session = session
        self._owns_session = session is None

    async def __aenter__(self) -> "HermesClient":
        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self

    async def __aexit__(self, *_exc) -> None:
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None:
            raise RuntimeError("HermesClient used outside its async context")
        return self._session

    def _headers(self, session_id: str, session_key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Hermes-Session-Id": session_id,
            "X-Hermes-Session-Key": session_key,
        }

    async def chat(
        self,
        messages: list[dict],
        *,
        guild_id: int,
        channel_id: int,
        model: str | None = None,
        timeout: float | None = None,
        reasoning_effort: str | None = None,
    ) -> str:
        session_id, session_key = session_ids(guild_id, channel_id)
        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
        }
        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort
        url = f"{self.endpoint}/chat/completions"
        try:
            async with self.session.post(
                url,
                json=payload,
                headers=self._headers(session_id, session_key),
                timeout=aiohttp.ClientTimeout(total=timeout or self.timeout),
            ) as response:
                if response.status >= 400:
                    body = (await response.text())[:500]
                    raise HermesError(f"Hermes {response.status}: {body}")
                data = await response.json(content_type=None)
        except aiohttp.ClientError as exc:
            raise HermesError(f"Hermes request failed: {exc}") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise HermesError("Hermes returned no choices[0].message.content") from exc
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") for part in content if isinstance(part, dict) and part.get("type") == "text"
            )
        return str(content or "").strip()

    @staticmethod
    def build_messages(system_prompt: str, attributed_text: str, image_parts: list[dict] | None = None) -> list[dict]:
        """Inline images into the same user turn as the attributed text."""
        if image_parts:
            content = [{"type": "text", "text": attributed_text}, *image_parts]
            return [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ]
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": attributed_text},
        ]
