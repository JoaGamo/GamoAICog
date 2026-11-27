"""Catalogue validation and the environment/chat overlay."""

import pytest

from gamoaicog.configspec import (
    ALL_SETTINGS,
    ENV_SETTINGS,
    apply_overrides,
    coerce,
    display,
    find_setting,
)
from gamoaicog.settings import Settings

BASE_ENV = {
    "LLM_ENDPOINT": "http://env-host:8642/v1",
    "LLM_API_KEY": "env-key",
    "LLM_MODEL": "env-model",
    "HINDSIGHT_API_URL": "http://env-hindsight:8888",
    "HINDSIGHT_API_KEY": "env-hs-key",
}


def test_every_setting_has_an_exact_example_and_a_lookup_alias():
    for spec in ALL_SETTINGS:
        assert spec.example, spec.key
        assert "[p]gamoai config" in spec.command
        assert find_setting(spec.name) is spec
        assert find_setting(spec.key) is spec
    assert find_setting("no-such-setting") is None


@pytest.mark.parametrize(
    ("name", "value", "expected"),
    [
        ("endpoint", "http://localhost", "http://localhost"),
        ("endpoint", "https://example.test/v1", "https://example.test/v1"),
        ("hindsight-url", "http://localhost:8888", "http://localhost:8888"),
        ("model", "gamoaibot", "gamoaibot"),
        ("media-max-bytes", "20971520", 20971520),
        ("hindsight-timeout", "30", 30.0),
        ("recall-budget", "mid", "mid"),
        ("enabled", "on", True),
        ("enabled", "off", False),
        ("chance", "20", 0.2),
        ("endpoint", "", None),
    ],
)
def test_coerce_accepts_documented_examples(name, value, expected):
    spec = find_setting(name)
    assert coerce(spec, value) == expected


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("endpoint", "localhost"),          # missing the http:// prefix
        ("vision-endpoint", "ftp://host"),
        ("hindsight-url", "hindsight:8888"),
        ("media-max-bytes", "mucho"),
        ("chance", "120"),
        ("recall-limit", "0"),
        ("enabled", "maybe"),
    ],
)
def test_coerce_rejects_bad_values_with_an_example(name, value):
    with pytest.raises(ValueError) as exc:
        coerce(find_setting(name), value)
    assert "Ejemplo:" in str(exc)


def test_secrets_are_never_rendered_by_display():
    spec = find_setting("hindsight-key")
    rendered = display(spec, "super-secret-value")
    assert "super-secret-value" not in rendered
    assert "oculto" in rendered


def test_display_uses_the_documented_percent_scale():
    assert display(find_setting("chance"), 0.2) == "20"


def test_apply_overrides_covers_every_environment_setting():
    cfg = {spec.key: f"chat-{spec.key}" for spec in ENV_SETTINGS}
    for spec in ENV_SETTINGS:
        if spec.url:
            cfg[spec.key] = "http://chat-host"
        elif spec.kind == "int":
            cfg[spec.key] = "7"
        elif spec.kind == "float":
            cfg[spec.key] = "7"
    settings = apply_overrides(Settings.from_env(BASE_ENV), cfg)
    for spec in ENV_SETTINGS:
        expected = coerce(spec, cfg[spec.key])
        assert getattr(settings, spec.key) == expected, spec.key


def test_blank_overrides_fall_back_to_environment():
    cfg = {spec.key: "" for spec in ENV_SETTINGS}
    settings = apply_overrides(Settings.from_env(BASE_ENV), cfg)
    assert settings.llm_endpoint == BASE_ENV["LLM_ENDPOINT"]
    assert settings.hindsight_api_key == BASE_ENV["HINDSIGHT_API_KEY"]


def test_vision_inherits_chat_overrides_layered_on_environment():
    env = {"LLM_API_KEY": "env-key"}
    cfg = {"llm_endpoint": "http://chat.test/v1", "llm_model": "chat-model"}
    settings = apply_overrides(Settings.from_env(env), cfg)

    assert settings.llm_endpoint == "http://chat.test/v1"
    assert settings.vision_endpoint == "http://chat.test/v1"
    assert settings.vision_api_key == "env-key"
    assert settings.vision_model == "chat-model"
    assert (settings.vision_endpoint, settings.vision_api_key) == (
        settings.llm_endpoint, settings.llm_api_key
    )


def test_explicit_vision_override_survives_the_fallback():
    env = {"LLM_API_KEY": "env-key"}
    cfg = {
        "llm_endpoint": "http://chat.test/v1",
        "vision_endpoint": "http://vision.test/v1",
        "vision_api_key": "vision-key",
    }
    settings = apply_overrides(Settings.from_env(env), cfg)

    assert settings.vision_endpoint == "http://vision.test/v1"
    assert settings.vision_api_key == "vision-key"
