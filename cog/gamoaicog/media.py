"""Discord media -> inline base64 for the OpenAI-compatible Hermes API.

Images are downloaded into a small local cache and sent inline; the API server
has no file-upload endpoint. YouTube links stay as URLs with an explicit note
so the gamoaibot profile can handle them with its video tools.
"""

from __future__ import annotations

import base64
import hashlib
import re
import time
from pathlib import Path
from typing import Any

import aiohttp

from .models import MediaAttachment

_YOUTUBE = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com/watch\?(?:[^\s#&]*&)?v=|youtu\.be/|youtube\.com/shorts/)([\w-]{11})",
    re.I,
)
_CACHE_TTL = 24 * 60 * 60


def youtube_ids(text: str) -> list[str]:
    return [match.group(1) for match in _YOUTUBE.finditer(text or "")]


class MediaPipeline:
    def __init__(
        self,
        cache_dir: str | Path,
        max_bytes: int = 20 * 1024 * 1024,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.max_bytes = max_bytes
        self._session = session
        self._owns_session = session is None

    async def __aenter__(self) -> "MediaPipeline":
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
            raise RuntimeError("MediaPipeline used outside its async context")
        return self._session

    def _cache_path(self, digest: str) -> Path:
        return self.cache_dir / f"{digest[:2]}" / digest

    def cleanup(self, now: float | None = None) -> int:
        """Remove cached files older than a day. Returns how many were removed."""
        now = time.time() if now is None else now
        removed = 0
        if not self.cache_dir.exists():
            return removed
        for path in self.cache_dir.rglob("*"):
            if not path.is_file():
                continue
            try:
                if now - path.stat().st_mtime > _CACHE_TTL:
                    path.unlink()
                    removed += 1
            except OSError:
                continue
        return removed

    async def prepare(self, message: Any) -> list[MediaAttachment]:
        """Download image attachments (duck-typed Discord message) and note others."""
        self.cleanup()
        attachments: list[MediaAttachment] = []
        for attachment in getattr(message, "attachments", ()) or ():
            mime = str(getattr(attachment, "content_type", "") or "").split(";")[0].strip().lower()
            filename = str(getattr(attachment, "filename", "") or "")
            size = int(getattr(attachment, "size", 0) or 0)
            url = str(getattr(attachment, "url", "") or "")
            if not url or not mime.startswith("image/"):
                continue
            if size and size > self.max_bytes:
                continue
            try:
                async with self.session.get(url) as response:
                    if response.status >= 400:
                        continue
                    data = await response.read()
            except aiohttp.ClientError:
                continue
            if len(data) > self.max_bytes:
                continue
            digest = hashlib.sha256(data).hexdigest()
            cache_path = self._cache_path(digest)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                cache_path.write_bytes(data)
            except OSError:
                pass  # cache is best-effort; the inline bytes still go through
            attachments.append(
                MediaAttachment(
                    url=url,
                    mime=mime,
                    filename=filename,
                    data_b64=base64.b64encode(data).decode("ascii"),
                )
            )
        return attachments

    @staticmethod
    def extra_context(text: str, attachments: list[MediaAttachment]) -> str:
        """Text notes for things the API cannot carry inline."""
        notes: list[str] = []
        for video_id in youtube_ids(text):
            notes.append(f"youtube:{video_id} (use the video tools to understand it)")
        for attachment in attachments:
            if not attachment.is_image:
                notes.append(attachment.as_text())
        return " | ".join(notes)
