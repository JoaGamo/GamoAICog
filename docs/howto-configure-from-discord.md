# How to configure GamoAI from Discord

Set, read or clear any cog setting as the bot owner without opening a terminal
on the Red host. Discord changes apply immediately, no cog reload needed.

## Prerequisites

- You are the Red bot owner.
- `gamoaicog` is loaded (`[p]load gamoaicog`).
- Use a DM with the bot for secret values. Anything typed in a channel is visible
  to everyone who can read that channel and may be logged by Discord.

`[p]` below is your Red command prefix.

## Steps

1. **See what is configured now.**

   ```text
   [p]gamoai config list
   ```

   Each line reads `name: value (source)`. `entorno` means the value comes from
   the environment; `chat` means a stored override is winning. Secrets show as
   `<oculto, N caracteres>`.

2. **Set a setting.** Pick a command name from the
   [configuration reference](config-reference.md). For example:

   ```text
   [p]gamoai config endpoint set http://hermes-host:8642/p/gamoaibot/v1
   [p]gamoai config hindsight-url set http://hindsight-host:8888
   [p]gamoai config chance set 20
   [p]gamoai config enabled set on
   ```

   The command replies with the new effective value. URLs must include
   `http://` or `https://`; `chance` is a percentage from 0 to 100.

3. **Read one setting back.**

   ```text
   [p]gamoai config endpoint get
   ```

   The reply includes the source, so you can tell whether you are looking at
   your override or at the environment.

4. **Clear an override.** Send `set` with an empty value:

   ```text
   [p]gamoai config endpoint set
   ```

   The setting falls back to the environment on the next turn. This is the way
   to undo a Discord change without editing any file.

5. **Set a secret.** Do this in a DM:

   ```text
   [p]gamoai config hindsight-key set <your-hindsight-key>
   ```

   The bot confirms the write but never prints the value. `get` and `list` show
   only its length.

6. **Allow a channel** by ID, from a DM or a channel:

   ```text
   [p]gamoai config channel add 123456789012345678
   [p]gamoai config channel list
   ```

7. **Check readiness.**

   ```text
   [p]gamoai status
   ```

   It reports `AI: on` and `Hindsight: on` when the effective credentials are
   present. It never prints keys.

## API_SERVER_* (the Hermes profile side)

The four `API_SERVER_*` variables configure the OpenAI-compatible API server of
the `gamoaibot` Hermes profile. They are **not** cog settings, so
`[p]gamoai config` does not expose them and cannot change them. They are read by
a different process from the one that runs the cog.

To change one:

1. Edit `~/.hermes/profiles/gamoaibot/.env` on the Hermes host. The template is
   `deploy/profile.env.example` in this repo. Keep `API_SERVER_HOST` on
   loopback and use a strong random `API_SERVER_KEY`.
2. Restart the process that serves the profile's API server (the standalone API
   server or the multiplexed gateway) so it re-reads the file. In gateway mode,
   one restart affects every profile sharing the gateway port.
3. Keep the cog and the profile in sync. The cog's `LLM_API_KEY` must equal the
   profile's `API_SERVER_KEY`. After changing the profile key, update the cog
   side in Discord, which takes effect immediately:

   ```text
   [p]gamoai config key set <same-value-as-api_server_key>
   ```

4. Reload the cog only if you changed the **cog's** service environment
   (`EnvironmentFile=` in Red's systemd unit), for example `LLM_ENDPOINT` or
   `MEDIA_CACHE_DIR` at the service level:

   ```text
   [p]reload gamoaicog
   ```

   Values set with `[p]gamoai config` never need a reload. Changing only the
   profile's `.env` needs an API server or gateway restart, not a cog reload.

Rule of thumb: Discord overrides are instant; environment files need their
own process to restart before the new value is read.

## Verification

- `[p]gamoai config list` shows the new value with source `chat`.
- `[p]gamoai config <setting> get` shows the same value and source.
- A blank `set` shows source `entorno` again.
- `[p]gamoai status` still reports AI and Hindsight as `on` after a key change.
- No `get`, `list` or `status` output contains a secret value.

## Troubleshooting

- **"URL inválida"** - the value needs an `http://` or `https://` prefix.
- **"Se esperaba un entero / número"** - the setting expects a number; check
  the example in the command help.
- **"Valor demasiado bajo/alto"** - the value is outside the range in the
  [reference table](config-reference.md#settings-with-an-environment-variable)
  or [behavior table](config-reference.md#behavior-settings).
- **`get` says `entorno` after a `set`** - you sent `set` with no value, which
  clears the override, or the command name was an alias you did not expect.
  Run `config list` to see the effective values.
- **AI is `off` after a change** - `LLM_ENDPOINT` or `LLM_API_KEY` is empty, or
  the cog's key no longer matches the profile's `API_SERVER_KEY`. Fix the cog
  side with `config endpoint set` / `config key set`, no reload required.
- **Hindsight is `off`** - `HINDSIGHT_API_URL` or `HINDSIGHT_API_KEY` is empty.
- **Changes vanished after a Red restart** - they are stored in Red Config and
  should persist. If they do not, check that the instance data path is the one
  Red is actually using; environment values are never written back to disk by
  the bot.

## Related

- [Configuration reference](config-reference.md)
- [Deployment](DEPLOYMENT.md)
- [README](../README.md)
