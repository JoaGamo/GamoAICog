"""Environment-driven settings: vision fallback and ai_enabled guard."""

import pytest

from cogaicog.settings import Settings

LLM = {
    "LLM_ENDPOINT": "http://llm.test/v1",
    "LLM_API_KEY": "chat-secret",
    "LLM_MODEL": "gamoaibot",
}


def test_vision_settings_fall_back_to_llm_settings():
    settings = Settings.from_env(dict(LLM))

    assert settings.vision_endpoint == "http://llm.test/v1"
    assert settings.vision_api_key == "chat-secret"
    assert settings.vision_model == "gamoaibot"


def test_explicit_vision_settings_override_the_fallback():
    env = {
        **LLM,
        "VISION_ENDPOINT": "http://vision.test/v1",
        "VISION_API_KEY": "vision-secret",
        "VISION_MODEL": "vision-model",
    }
    settings = Settings.from_env(env)

    assert settings.vision_endpoint == "http://vision.test/v1"
    assert settings.vision_api_key == "vision-secret"
    assert settings.vision_model == "vision-model"
    assert settings.llm_endpoint == "http://llm.test/v1"


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({}, False),
        ({"LLM_ENDPOINT": "http://llm.test/v1"}, False),
        ({"LLM_API_KEY": "chat-secret"}, False),
        ({"LLM_ENDPOINT": "http://llm.test/v1", "LLM_API_KEY": "chat-secret"}, True),
        ({"LLM_ENDPOINT": "   ", "LLM_API_KEY": "chat-secret"}, False),
        ({"LLM_ENDPOINT": "http://llm.test/v1", "LLM_API_KEY": "   "}, False),
    ],
)
def test_ai_enabled_requires_both_endpoint_and_key(env, expected):
    assert Settings.from_env(env).ai_enabled is expected
