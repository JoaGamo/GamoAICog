"""Catalogue of every cog setting that can be changed from Discord.

The environment is the base layer; chat overrides live in Red Config and are
re-applied by ``apply_overrides`` on every settings refresh. Each spec also
carries the exact example printed in its Discord command help.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .settings import Settings


@dataclass(frozen=True)
class SettingSpec:
    key: str
    name: str
    example: str
    description: str
    env: str = ""
    kind: str = "str"
    secret: bool = False
    url: bool = False
    minimum: float | None = None
    maximum: float | None = None
    scale: float = 1.0
    aliases: tuple[str, ...] = field(default_factory=tuple)

    @property
    def label(self) -> str:
        """Name shown in Discord messages."""
        return self.env or self.key.upper()

    @property
    def command(self) -> str:
        return f"[p]gamoai config {self.name}"


ENV_SETTINGS: tuple[SettingSpec, ...] = (
    SettingSpec(
        key="llm_endpoint", env="LLM_ENDPOINT", name="endpoint",
        aliases=("llm_endpoint", "chat-endpoint"),
        example="http://localhost", url=True,
        description="Endpoint chat (gamoaibot API de Hermes).",
    ),
    SettingSpec(
        key="llm_api_key", env="LLM_API_KEY", name="key",
        aliases=("llm_key", "llm_api_key", "chat-key"),
        example="replace-with-the-profile-API_SERVER_KEY", secret=True,
        description="Bearer key del API de Hermes (ofuscada en `get`).",
    ),
    SettingSpec(
        key="llm_model", env="LLM_MODEL", name="model",
        aliases=("llm_model", "chat-model"), example="gamoaibot",
        description="Modelo usado en respuestas de chat.",
    ),
    SettingSpec(
        key="vision_endpoint", env="VISION_ENDPOINT", name="vision-endpoint",
        aliases=("vision_endpoint",), example="http://localhost", url=True,
        description="Endpoint multimodal; vacío usa el endpoint chat.",
    ),
    SettingSpec(
        key="vision_api_key", env="VISION_API_KEY", name="vision-key",
        aliases=("vision_key", "vision_api_key"),
        example="replace-with-vision-key", secret=True,
        description="Bearer key del endpoint vision (ofuscada en `get`).",
    ),
    SettingSpec(
        key="vision_model", env="VISION_MODEL", name="vision-model",
        aliases=("vision_model",), example="gamoaibot",
        description="Modelo usado en turnos con imágenes.",
    ),
    SettingSpec(
        key="hindsight_api_url", env="HINDSIGHT_API_URL", name="hindsight-url",
        aliases=("hindsight_api_url", "hindsight-endpoint"),
        example="http://localhost:8888", url=True,
        description="URL base de la API REST de Hindsight.",
    ),
    SettingSpec(
        key="hindsight_api_key", env="HINDSIGHT_API_KEY", name="hindsight-key",
        aliases=("hindsight_api_key",),
        example="replace-with-hindsight-key", secret=True,
        description="API key de Hindsight (ofuscada en `get`).",
    ),
    SettingSpec(
        key="hindsight_timeout", env="HINDSIGHT_TIMEOUT", name="hindsight-timeout",
        aliases=("hindsight_timeout",), example="30", kind="float", minimum=0.1,
        description="Timeout de llamadas Hindsight, en segundos.",
    ),
    SettingSpec(
        key="hermes_timeout", env="HERMES_TIMEOUT", name="hermes-timeout",
        aliases=("hermes_timeout",), example="120", kind="float", minimum=0.1,
        description="Timeout de llamadas al API de Hermes, en segundos.",
    ),
    SettingSpec(
        key="media_cache_dir", env="MEDIA_CACHE_DIR", name="media-cache-dir",
        aliases=("media_cache_dir",), example="runtime/media-cache",
        description="Directorio local de cache de multimedia.",
    ),
    SettingSpec(
        key="media_max_bytes", env="MEDIA_MAX_BYTES", name="media-max-bytes",
        aliases=("media_max_bytes",), example="20971520", kind="int", minimum=1,
        description="Tamaño máximo de un archivo multimedia, en bytes.",
    ),
    SettingSpec(
        key="recall_budget", env="RECALL_BUDGET", name="recall-budget",
        aliases=("recall_budget",), example="mid",
        description="Budget de recall de Hindsight.",
    ),
    SettingSpec(
        key="recall_limit", env="RECALL_LIMIT", name="recall-limit",
        aliases=("recall_limit",), example="5", kind="int", minimum=1,
        description="Máximo de recuerdos inyectados por bank.",
    ),
)

BEHAVIOR_SETTINGS: tuple[SettingSpec, ...] = (
    SettingSpec(
        key="chance", name="chance", example="20", kind="float",
        minimum=0, maximum=100, scale=100,
        description="Chance de respuesta random, en porcentaje (0-100).",
    ),
    SettingSpec(
        key="cooldown", name="cooldown", example="30", kind="float", minimum=0,
        description="Cooldown por canal, en segundos.",
    ),
    SettingSpec(
        key="buffer_count", name="buffer-count", aliases=("buffer_count",),
        example="15", kind="int", minimum=1,
        description="Mensajes pasivos antes de hacer flush a Hindsight.",
    ),
    SettingSpec(
        key="buffer_idle", name="buffer-idle", aliases=("buffer_idle",),
        example="180", kind="float", minimum=1,
        description="Segundos de inactividad antes de hacer flush.",
    ),
    SettingSpec(
        key="enabled", name="enabled", example="on", kind="bool",
        description="Activa o desactiva las respuestas de GamoAI.",
    ),
)

ALL_SETTINGS: tuple[SettingSpec, ...] = ENV_SETTINGS + BEHAVIOR_SETTINGS


def find_setting(name: str) -> SettingSpec | None:
    """Look up by command name or alias, case-insensitively."""
    wanted = name.strip().lower().replace("_", "-")
    for spec in ALL_SETTINGS:
        candidates = (spec.name, *spec.aliases, spec.key)
        if wanted in {candidate.lower().replace("_", "-") for candidate in candidates}:
            return spec
    return None


def coerce(spec: SettingSpec, raw: str) -> Any:
    """Validate chat input and return the *stored* value.

    An empty string means "clear the chat override and use the environment".
    Raises ValueError with an exact example, safe to echo back to Discord.
    """
    value = (raw or "").strip()
    if not value:
        return None
    if spec.url and not value.lower().startswith(("http://", "https://")):
        raise ValueError(f"URL inválida. Ejemplo: {spec.example}")
    if spec.kind in ("int", "float"):
        try:
            number = int(value) if spec.kind == "int" else float(value)
        except ValueError:
            kind = "entero" if spec.kind == "int" else "número"
            raise ValueError(f"Se esperaba un {kind}. Ejemplo: {spec.example}") from None
        if spec.minimum is not None and number < spec.minimum:
            raise ValueError(f"Valor demasiado bajo. Ejemplo: {spec.example}")
        if spec.maximum is not None and number > spec.maximum:
            raise ValueError(f"Valor demasiado alto. Ejemplo: {spec.example}")
        return number / spec.scale
    if spec.kind == "bool":
        if value.lower() in ("on", "true", "1", "yes", "si", "sí"):
            return True
        if value.lower() in ("off", "false", "0", "no"):
            return False
        raise ValueError(f"Usá on u off. Ejemplo: {spec.example}")
    return value


def display(spec: SettingSpec, stored: Any) -> str:
    """Render a stored value for chat. Secrets are never revealed."""
    if stored is None or stored == "":
        return "<sin override, usa entorno>" if spec.env else "<sin valor>"
    if spec.secret:
        return f"<oculto, {len(str(stored))} caracteres>"
    value = stored * spec.scale if spec.scale != 1 and isinstance(stored, (int, float)) else stored
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def override_source(spec: SettingSpec, cfg: Mapping[str, Any]) -> str:
    """Where the effective value comes from: chat override or environment."""
    value = cfg.get(spec.key)
    return "chat" if value is not None and value != "" else "entorno"


def apply_overrides(settings: Settings, cfg: Mapping[str, Any]) -> Settings:
    """Layer every chat override on top of an environment-derived Settings."""
    changes: dict[str, Any] = {}
    for spec in ENV_SETTINGS:
        value = cfg.get(spec.key)
        if value is None or value == "":
            continue
        changes[spec.key] = coerce(spec, str(value))
    return settings.with_overrides(**changes)
