"""The `config` command surface: binding, examples, validation and secrecy."""

import os

import pytest

from gamoaicog.buffer import ChannelManager
from gamoaicog.cog import GamoAICog
from gamoaicog.configspec import ALL_SETTINGS, find_setting
from gamoaicog.settings import Settings

ENV = {
    "LLM_ENDPOINT": "http://env-host:8642/v1",
    "LLM_API_KEY": "env-key",
    "LLM_MODEL": "env-model",
    "HINDSIGHT_API_URL": "http://env-hindsight:8888",
    "HINDSIGHT_API_KEY": "env-hs-key",
}


class FakeConfigValue:
    def __init__(self, store, key):
        self.store = store
        self.key = key

    async def set(self, value):
        self.store[self.key] = value


class FakeConfig:
    def __init__(self, data):
        self.data = data

    def __getattr__(self, key):
        return FakeConfigValue(self.data, key)

    async def all(self):
        return dict(self.data)


class FakeCtx:
    def __init__(self):
        self.sent = []

    async def send(self, text):
        self.sent.append(str(text))

    async def tick(self):
        self.sent.append("tick")


@pytest.fixture
def cog(monkeypatch):
    monkeypatch.setattr(os, "environ", dict(ENV))
    data = {spec.key: (0.2 if spec.key == "chance" else None) for spec in ALL_SETTINGS}
    data.update(
        {
            "enabled": True,
            "channels": [],
            "cooldown": 30.0,
            "buffer_count": 15,
            "buffer_idle": 180.0,
        }
    )
    instance = object.__new__(GamoAICog)
    instance.config = FakeConfig(data)
    instance.settings = Settings.from_env(ENV)
    instance.manager = ChannelManager()
    instance._session = object()
    return instance


def _config_group():
    gamoai = next(c for c in GamoAICog.__cog_commands__ if c.name == "gamoai")
    return next(c for c in gamoai.commands if c.name == "config")


def test_every_config_command_has_set_get_and_an_exact_example():
    config = _config_group()
    assert "http://localhost" in config.help
    groups = {c.name: c for c in config.commands}
    for spec in ALL_SETTINGS:
        group = groups[spec.name]
        children = {c.name: c for c in group.commands}
        assert set(children) == {"set", "get"}, spec.name
        assert "Example:" in group.help, spec.name
        assert f"config {spec.name} set {spec.example}" in children["set"].help, spec.name
        assert f"config {spec.name} get" in children["get"].help, spec.name
    for name in ("channel", "list"):
        assert "Example:" in groups[name].help


def test_every_config_command_is_bound_in_the_class_namespace():
    """Unbound generated commands fail at invocation with a missing ctx."""
    groups = {c.name: c for c in _config_group().commands}
    for spec in ALL_SETTINGS:
        base = f"config_{spec.name.replace('-', '_')}"
        group = groups[spec.name]
        children = {c.name: c for c in group.commands}
        assert getattr(GamoAICog, base) is group, spec.key
        assert getattr(GamoAICog, f"{base}_set") is children["set"], spec.key
        assert getattr(GamoAICog, f"{base}_get") is children["get"], spec.key


def test_config_commands_do_not_parse_ctx_as_a_user_argument():
    """Red must skip self and ctx; otherwise invocation dies in conversion."""
    config = _config_group()
    for item in config.commands:
        commands_to_check = [item, *getattr(item, "commands", ())]
        for command in commands_to_check:
            assert "<locals>" not in command.callback.__qualname__, command.qualified_name
            assert "self" not in command.params, command.qualified_name
            assert "ctx" not in command.params, command.qualified_name


@pytest.mark.asyncio
async def test_endpoint_set_validates_the_http_prefix_and_applies_the_value(cog):
    ctx = FakeCtx()
    setter = next(c.callback for c in _config_group().commands
                  if c.name == "endpoint" for c in c.commands if c.name == "set")
    await setter(cog, ctx, value="localhost")
    assert "http://localhost" in ctx.sent[-1]
    assert cog.config.data["llm_endpoint"] is None

    await setter(cog, ctx, value="http://localhost")
    assert cog.config.data["llm_endpoint"] == "http://localhost"
    assert cog.settings.llm_endpoint == "http://localhost"


@pytest.mark.asyncio
async def test_secrets_are_stored_but_never_echoed(cog):
    ctx = FakeCtx()
    group = next(c for c in _config_group().commands if c.name == "hindsight-key")
    setter = next(c for c in group.commands if c.name == "set")
    getter = next(c for c in group.commands if c.name == "get")

    await setter(cog, ctx, value="super-secret-value")
    assert cog.config.data["hindsight_api_key"] == "super-secret-value"
    assert all("super-secret-value" not in msg for msg in ctx.sent)

    await getter(cog, ctx)
    assert "super-secret-value" not in ctx.sent[-1]
    assert "oculto" in ctx.sent[-1]
    assert "chat" in ctx.sent[-1]


@pytest.mark.asyncio
async def test_blank_set_clears_an_override_back_to_environment(cog):
    ctx = FakeCtx()
    group = next(c for c in _config_group().commands if c.name == "endpoint")
    setter = next(c for c in group.commands if c.name == "set")
    getter = next(c for c in group.commands if c.name == "get")

    await setter(cog, ctx, value="http://chat-host")
    assert cog.settings.llm_endpoint == "http://chat-host"
    await setter(cog, ctx, value="")
    assert cog.config.data["llm_endpoint"] is None
    assert cog.settings.llm_endpoint == ENV["LLM_ENDPOINT"]
    await getter(cog, ctx)
    assert "entorno" in ctx.sent[-1]


@pytest.mark.asyncio
async def test_percent_setting_is_displayed_as_a_percentage(cog):
    ctx = FakeCtx()
    group = next(c for c in _config_group().commands if c.name == "chance")
    setter = next(c for c in group.commands if c.name == "set")
    getter = next(c for c in group.commands if c.name == "get")

    await setter(cog, ctx, value="20")
    assert cog.config.data["chance"] == pytest.approx(0.2)
    await getter(cog, ctx)
    assert "20" in ctx.sent[-1]


@pytest.mark.asyncio
async def test_list_masks_secrets_and_shows_sources(cog):
    ctx = FakeCtx()
    cmd = next(c.callback for c in _config_group().commands if c.name == "list")
    cog.config.data["hindsight_api_key"] = "super-secret-value"
    await cmd(cog, ctx)
    joined = "\n".join(ctx.sent)
    assert "super-secret-value" not in joined
    assert "hindsight-key:" in joined
    assert "endpoint: http://env-host:8642/v1 (entorno)" in joined
    assert "hindsight-key: <oculto, 18 caracteres> (chat)" in joined


def test_all_settings_are_reachable_from_chat():
    config = _config_group()
    names = {c.name for c in config.commands}
    assert {spec.name for spec in ALL_SETTINGS} <= names
    assert {"channel", "list"} <= names
