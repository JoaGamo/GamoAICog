# Configuration reference

Every GamoAI setting has two possible sources. The **environment** is the base
layer (loaded from Red's service environment at cog load). A **chat override**
lives in Red Config and wins over the environment when present. Both can be
inspected from Discord.

For step-by-step instructions, see [How to configure GamoAI from Discord](howto-configure-from-discord.md).

## Command shape

```text
[p]gamoai config <setting> set <value>
[p]gamoai config <setting> get
[p]gamoai config list
[p]gamoai config channel add <channel_id>
[p]gamoai config channel remove <channel_id>
[p]gamoai config channel list
```

`[p]` is your Red command prefix. All `gamoai` commands require the Red bot
owner ID, including every `config` subcommand: the check is inherited from the
`gamoai` group. They work in DMs. Calling a setting group with no subcommand
prints its help, which always contains an exact example.

## Value rules

- A blank `set` clears the chat override for that setting. The effective value
  falls back to the environment.
- URL settings (`endpoint`, `vision-endpoint`, `hindsight-url`) require an
  `http://` or `https://` prefix. Validation errors include the exact example.
- `chance` is entered as a percentage from 0 to 100 and stored as a 0..1
  fraction. `get` displays it as a percentage.
- Booleans accept `on`, `true`, `1`, `yes`, `si`, `sí` or `off`, `false`, `0`, `no`.
- Integers and floats are range-checked; invalid values are rejected with an
  `Ejemplo:` message copied into Discord.
- Secret values are stored in Red Config and never echoed. `get` and `list`
  render them as `<oculto, N caracteres>`.
- Settings with an environment variable accept the variable name as a command
  alias. For example, `config llm_endpoint get` is the same as
  `config endpoint get`. Underscores and hyphens are interchangeable in aliases.

`[p]gamoai config list` prints all 19 settings as `name: value (source)`, where
source is `chat` (a stored override) or `entorno` (the environment). Long output
is split into Discord-sized code blocks.

## Settings with an environment variable

These 14 settings map one-to-one to cog environment variables. Defaults in the
table are the values used when the variable is unset and no chat override exists.

| Command | Env var | Type / default | Constraints |
|---|---|---|---|
| `endpoint` | `LLM_ENDPOINT` | URL, empty | Must start with `http://` or `https://` |
| `key` | `LLM_API_KEY` | secret string, empty | Must match the profile's `API_SERVER_KEY` |
| `model` | `LLM_MODEL` | string, `gamoaibot` | - |
| `vision-endpoint` | `VISION_ENDPOINT` | URL, empty | Blank uses `endpoint` |
| `vision-key` | `VISION_API_KEY` | secret string, empty | Blank uses `key` |
| `vision-model` | `VISION_MODEL` | string, empty | Blank uses `model` |
| `hindsight-url` | `HINDSIGHT_API_URL` | URL, `http://localhost:8888` | Must start with `http://` or `https://` |
| `hindsight-key` | `HINDSIGHT_API_KEY` | secret string, empty | - |
| `hindsight-timeout` | `HINDSIGHT_TIMEOUT` | float, `30` | Minimum `0.1`, seconds |
| `hermes-timeout` | `HERMES_TIMEOUT` | float, `120` | Minimum `0.1`, seconds |
| `media-cache-dir` | `MEDIA_CACHE_DIR` | string, `runtime/media-cache` | Local path on the Red host |
| `media-max-bytes` | `MEDIA_MAX_BYTES` | int, `20971520` | Minimum `1`, bytes |
| `recall-budget` | `RECALL_BUDGET` | string, `mid` | Hindsight recall budget |
| `recall-limit` | `RECALL_LIMIT` | int, `5` | Minimum `1`, memories per bank |

The three key settings (`key`, `vision-key`, `hindsight-key`) are secrets and
are always masked in Discord output.

When `LLM_ENDPOINT` or `LLM_API_KEY` resolves to empty, the cog stays loaded but
makes no AI calls. When `HINDSIGHT_API_KEY` is empty, memory recall and retain
are skipped.

## Behavior settings

These five have no environment variable. Their values live only in Red Config.

| Command | Default | Constraints | Effect |
|---|---|---|---|
| `chance` | `20` | 0-100, entered as percent | Chance of a random reply in an allowed channel |
| `cooldown` | `30` | Minimum `0`, seconds | Per-channel gap after a reply; mentions and direct replies bypass it |
| `buffer-count` | `15` | Minimum `1` | Passive messages before a Hindsight flush |
| `buffer-idle` | `180` | Minimum `1`, seconds | Idle time before a passive flush |
| `enabled` | `on` | Boolean | Master switch for AI replies |

## Channel allowlist

`config channel add|remove|list` uses numeric channel IDs and works in DMs.
The older `gamoai channel add|remove|list` accepts a Discord channel object and
renders it as a mention. Both commands edit the same allowlist. Messages are
ignored outside allowed channels, in DMs, and in NSFW channels.

## Settings that are not in Discord

`API_SERVER_ENABLED`, `API_SERVER_HOST`, `API_SERVER_PORT` and `API_SERVER_KEY`
belong to the `gamoaibot` Hermes profile, a different process from the cog.
`[p]gamoai config` does not expose them and cannot change them. They live in the
profile's `.env` (`~/.hermes/profiles/gamoaibot/.env`; template
`deploy/profile.env.example`). See
[How to configure GamoAI from Discord](howto-configure-from-discord.md) under
"API_SERVER_* (the Hermes profile side)" for the procedure and the reload/restart
rules.

## Related

- [How to configure GamoAI from Discord](howto-configure-from-discord.md)
- [Deployment](DEPLOYMENT.md)
- [README](../README.md)
