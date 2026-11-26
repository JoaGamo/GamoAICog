# GamoAI

Hermes-backed chat cog for an existing Red-Discordbot instance. One bot identity, guild-scoped long-term memory, casual random replies in allowed channels.

Architecture is summarized here and in `docs/DEPLOYMENT.md`; change the locked behavior deliberately.

## Layout

```
distribution.yaml   Hermes profile distribution manifest (gamoaibot)
config.yaml         Non-secret profile defaults (native memory disabled)
PERSONA.md          Copy into the profile's SOUL.md
info.json           Repo metadata for Red's Downloader (`[p]cog repo add`)
gamoaicog/          Installable cog package (has its own info.json + setup())
deploy/             profile.env.example, cog.env.example, systemd unit
cog/gamoai.py       Legacy single-file entry point (manual installs only)
tests/              Unit + opt-in integration tests
runtime/            Local-only media cache and terminal cwd (gitignored)
```

## How it works

- The Red cog owns Discord behavior: trigger policy, allowlist, cooldown, media download, speaker prefixes and every Hindsight REST call.
- The `gamoaibot` Hermes profile owns the agent loop and response generation. It is reached over its loopback OpenAI-compatible API server at `POST /v1/chat/completions`.
- Sessions are channel-scoped: `X-Hermes-Session-Id: discord-<guild_id>-<channel_id>` and `X-Hermes-Session-Key: discord:<guild_id>:<channel_id>`.
- Memory banks are computed in the cog: `gamoaibot-user-<guild_id>-<user_id>` and `gamoaibot-guild-<guild_id>`. Nothing is shared across guilds. Hermes' native Hindsight provider is disabled on the profile.
- Default random reply chance is **0%**: the bot stays quiet until the owner opts in.

## Quick start

See `docs/DEPLOYMENT.md`. Short version:

1. `hermes profile install github.com/JoaGamo/GamoAICog --name gamoaibot` (or use the local checkout), copy `deploy/profile.env.example` to the profile `.env`, fill it, disable dangerous toolsets, start the API server.
2. On the Red host, install as a community cog: `[p]cog repo add GamoAI https://github.com/JoaGamo/GamoAICog` then `[p]cog install GamoAI gamoaicog`. The repo is private, so Red's host needs git credentials. Downloader does not load `.env`: put the cog variables from `deploy/cog.env.example` into Red's service environment (`EnvironmentFile=` in its systemd unit), then `[p]load gamoaicog`.
3. As bot owner: `[p]gamoai channel add #channel`, `[p]gamoai chance 5`, `[p]gamoai status`.

No `DISCORD_BOT_TOKEN` is needed anywhere: Red already authenticates to Discord. The profile is not a Discord gateway and the cog is not a standalone bot.

Secrets are never committed. `LLM_*` and `VISION_*` are the cog's view of the Hermes API server; `VISION_*` falls back to `LLM_*` when blank. If `LLM_ENDPOINT` or `LLM_API_KEY` is missing, the cog loads but makes no AI calls.

## Owner commands

All commands require the Red bot owner ID.

| Command | Effect |
|---|---|
| `gamoai status` | Config summary, AI/Hindsight readiness, buffered counts (no secrets) |
| `gamoai toggle` | Enable/disable AI replies |
| `gamoai channel add/remove/list [channel]` | Channel allowlist |
| `gamoai chance <0-100>` | Random reply chance (default 0) |
| `gamoai cooldown <seconds>` | Per-channel cooldown (default 30) |
| `gamoai buffer <count> <idle_seconds>` | Passive flush thresholds (default 15 / 180) |
| `gamoai model chat/vision <name>` | Runtime model override |
| `gamoai endpoint chat/vision <url>` | Runtime endpoint override |
| `gamoai purge bank <guild_id> <user_id>` | Delete one user bank |
| `gamoai purge guild <guild_id>` | Delete one guild bank |

API keys stay in env, never in Red config or Discord commands.

## Tests

```bash
uv venv .venv && uv pip install -r requirements-dev.txt
.venv/bin/pytest -q
```

Integration tests are opt-in and use disposable `gamoaibot-test-*` banks:

```bash
GAMOAI_INTEGRATION=1 .venv/bin/pytest -q tests/integration -m integration
```
