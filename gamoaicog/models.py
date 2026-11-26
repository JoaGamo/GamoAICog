"""Small value types passed between the cog and its helper modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class MediaAttachment:
    url: str
    mime: str
    filename: str = ""
    data_b64: str = ""

    @property
    def is_image(self) -> bool:
        return self.mime.lower().startswith("image/")

    def as_image_part(self) -> dict:
        """OpenAI-compatible inline image part (no file-upload support)."""
        return {
            "type": "image_url",
            "image_url": {"url": f"data:{self.mime};base64,{self.data_b64}"},
        }

    def as_text(self) -> str:
        return f"[attached: {self.filename or self.mime}]"


@dataclass(frozen=True)
class ChatMessage:
    guild_id: int
    channel_id: int
    author_id: int
    author_name: str
    text: str
    message_id: int = 0
    media: tuple[MediaAttachment, ...] = field(default_factory=tuple)
    is_mention: bool = False
    sent_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def speaker(self) -> str:
        return f"[@{self.author_name}|{self.author_id}]"

    def attributed_text(self) -> str:
        """Source of truth for speaker attribution sent to Hermes."""
        return f"{self.speaker} {self.text}".strip()

    def to_dict(self) -> dict:
        return {
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "text": self.text,
            "message_id": self.message_id,
        }
