"""Environment-driven settings for the GamoAI cog.

Secrets come from the process environment (loaded from cog/.env by the entry
point). Nothing here is written back to disk or sent over Discord.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from typing import Mapping


def _float(env: Mapping[str, str], key: str, default: float) -> float:
    raw = str(env.get(key, "") or "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _int(env: Mapping[str, str], key: str, default: int) -> int:
    return int(_float(env, key, float(default)))


@dataclass(frozen=True)
class Settings:
    llm_endpoint: str = ""
    llm_api_key: str = ""
    llm_model: str = "gamoaibot"
    vision_endpoint: str = ""
    vision_api_key: str = ""
    vision_model: str = ""
    hindsight_api_url: str = "http://localhost:8888"
    hindsight_api_key: str = ""
    hindsight_timeout: float = 30.0
    hermes_timeout: float = 120.0
    media_cache_dir: str = "runtime/media-cache"
    media_max_bytes: int = 20 * 1024 * 1024
    recall_budget: str = "mid"
    recall_limit: int = 5

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        e: Mapping[str, str] = os.environ if env is None else env

        def get(key: str, default: str = "") -> str:
            return str(e.get(key, default) or "").strip()

        llm_endpoint = get("LLM_ENDPOINT")
        llm_api_key = get("LLM_API_KEY")
        llm_model = get("LLM_MODEL", "gamoaibot")

        return cls(
            llm_endpoint=llm_endpoint,
            llm_api_key=llm_api_key,
            llm_model=llm_model,
            vision_endpoint=get("VISION_ENDPOINT"),
            vision_api_key=get("VISION_API_KEY"),
            vision_model=get("VISION_MODEL"),
            hindsight_api_url=get("HINDSIGHT_API_URL", "http://localhost:8888"),
            hindsight_api_key=get("HINDSIGHT_API_KEY"),
            hindsight_timeout=_float(e, "HINDSIGHT_TIMEOUT", 30.0),
            hermes_timeout=_float(e, "HERMES_TIMEOUT", 120.0),
            media_cache_dir=get("MEDIA_CACHE_DIR", "runtime/media-cache"),
            media_max_bytes=_int(e, "MEDIA_MAX_BYTES", 20 * 1024 * 1024),
            recall_budget=get("RECALL_BUDGET", "mid"),
            recall_limit=_int(e, "RECALL_LIMIT", 5),
        )

    def with_vision_fallback(self) -> "Settings":
        """Blank VISION_* inherits the effective LLM_* values.

        Must run after chat overrides are layered: the LLM endpoint may come
        from Red Config while the environment only holds a key. Resolving the
        fallback earlier leaves the vision client with an empty base URL.
        """
        return replace(
            self,
            vision_endpoint=self.vision_endpoint or self.llm_endpoint,
            vision_api_key=self.vision_api_key or self.llm_api_key,
            vision_model=self.vision_model or self.llm_model,
        )

    @property
    def ai_enabled(self) -> bool:
        """False means: stay loaded, make no Hermes calls at all."""
        return bool(self.llm_endpoint and self.llm_api_key)

    @property
    def hindsight_enabled(self) -> bool:
        return bool(self.hindsight_api_url and self.hindsight_api_key)

    def with_overrides(self, **changes: object) -> "Settings":
        return replace(self, **changes)
