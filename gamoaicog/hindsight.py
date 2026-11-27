"""Thin async client for the Hindsight REST API.

The Red cog computes bank IDs and owns every retain/recall/purge call. No
Hermes plugin, template or native provider is involved.
"""

from __future__ import annotations

from urllib.parse import quote

import aiohttp


class HindsightError(RuntimeError):
    pass


def memory_item(
    content: str,
    *,
    tags: list[str],
    document_id: str | None = None,
    timestamp: str | None = None,
    context: str | None = None,
) -> dict:
    """Build one MemoryItem with the flat key:value tag vocabulary."""
    item = {"content": content, "tags": tags}
    if document_id:
        item["document_id"] = document_id
    if timestamp:
        item["timestamp"] = timestamp
    if context:
        item["context"] = context
    return item


class HindsightClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._session = session
        self._owns_session = session is None

    async def __aenter__(self) -> "HindsightClient":
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
            raise RuntimeError("HindsightClient used outside its async context")
        return self._session

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _url(self, bank_id: str, suffix: str = "") -> str:
        return f"{self.base_url}/v1/default/banks/{quote(bank_id, safe='')}{suffix}"

    async def _request(self, method: str, url: str, **kwargs) -> dict:
        try:
            async with self.session.request(
                method, url, headers=self._headers(), timeout=aiohttp.ClientTimeout(total=self.timeout), **kwargs
            ) as response:
                if response.status >= 400:
                    body = (await response.text())[:500]
                    raise HindsightError(f"Hindsight {method} {url} -> {response.status}: {body}")
                if response.status == 204:
                    return {}
                return await response.json(content_type=None)
        except aiohttp.ClientError as exc:
            raise HindsightError(f"Hindsight {method} {url} failed: {exc}") from exc

    async def recall(
        self,
        bank_id: str,
        query: str,
        *,
        tags: list[str] | None = None,
        budget: str = "mid",
        limit: int = 5,
    ) -> list[dict]:
        payload: dict[str, object] = {"query": query, "budget": budget}
        if tags:
            payload["tags"] = tags
            payload["tags_match"] = "any"
        data = await self._request("POST", self._url(bank_id, "/memories/recall"), json=payload)
        results = data.get("results") or []
        return [
            {
                "text": str(item.get("text") or ""),
                "type": item.get("type"),
                "context": item.get("context"),
                "tags": item.get("tags") or [],
            }
            for item in results[:limit]
            if item.get("text")
        ]

    async def retain(self, bank_id: str, items: list[dict]) -> None:
        if not items:
            return
        await self._request(
            "POST",
            self._url(bank_id, "/memories"),
            # Async consolidation: Hindsight returns immediately with an operation
            # id. Synchronous retain can take minutes on a loaded server and was
            # timing out the cog's 30s client timeout.
            json={"items": items, "async": True},
        )

    async def purge(self, bank_id: str) -> bool:
        """Delete a whole bank. Returns False when it did not exist."""
        try:
            await self._request("DELETE", self._url(bank_id))
            return True
        except HindsightError as exc:
            if "404" in str(exc):
                return False
            raise

    @staticmethod
    def format_context(results: list[dict], label: str) -> str:
        if not results:
            return ""
        lines = [f"[{label}]"]
        for item in results:
            context = f" ({item['context']})" if item.get("context") else ""
            lines.append(f"- {item['text']}{context}")
        return "\n".join(lines)
