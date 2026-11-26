# Deployment

The cog runs inside your existing Red-Discordbot instance. No second Discord
application or bot token is needed for production; Red owns Discord auth.

## 1. Hermes profile

```bash
# From this checkout (or after `hermes profile install <repo> --name gamoaibot`):
cp config.yaml ~/.hermes/profiles/gamoaibot/config.yaml
cp PERSONA.md ~/.hermes/profiles/gamoaibot/SOUL.md
cp deploy/profile.env.example ~/.hermes/profiles/gamoaibot/.env
$EDITOR ~/.hermes/profiles/gamoaibot/.env        # fill values; never commit
mkdir -p runtime

# Native Hindsight must be off on this profile: the cog owns the banks.
hermes -p gamoaibot config set memory.provider ""
hermes -p gamoaibot config set memory.memory_enabled false
hermes -p gamoaibot config set memory.user_profile_enabled false
# Configure the model/provider you want this profile to use:
hermes -p gamoaibot model
# memory.auto_retain / auto_recall are not config.yaml keys in Hermes 0.23;
# the real guard is that the hindsight plugin is not installed in this profile.
hermes -p gamoaibot plugins list | grep -i hindsight   # must print nothing
hermes -p gamoaibot plugins disable hindsight          # no-op if absent

# The API server platform has its own toolset config. Restrict it there.
hermes -p gamoaibot tools disable --platform api_server terminal browser file code_execution image_gen memory session_search connections delegation cronjob todo
hermes -p gamoaibot tools enable --platform api_server video vision skills web
hermes -p gamoaibot tools list --platform api_server
```

Hermes 0.23 can run a **multiplexed gateway**: one process serves every profile. In that mode `hermes -p gamoaibot gateway run` reports "already served" and exits; the profile is selected by a named path prefix and authenticated with that profile's own `API_SERVER_KEY`:

```bash
curl -s -H "Authorization: Bearer <profile API_SERVER_KEY>" \
  http://<HERMES_HOST>:8642/p/gamoaibot/v1/models
```

Set the cog's `LLM_ENDPOINT` to the same URL. Keep the API unreachable from
untrusted networks; if several profiles share the port, firewall changes affect
all of them.

## 2. Red cog

On the Red host (which needs git access to the repo):

```bash
# In Discord, as bot owner:
[p]cog repo add GamoAI <repository-url>
[p]cog install GamoAI gamoaicog
```

There is one canonical cog-side env file: `cog/.env` (gitignored). `deploy/cog.env.example` is only a template; copy it to `cog/.env` on a fresh host. On the Red host, point the service's `EnvironmentFile=` at that file (or sync it there). Downloader does not load `.env` from the cog directory by itself. Then `[p]load gamoaicog`.

For a manual install instead of Downloader, copy the `gamoaicog/` directory into the instance's CogManager install path (`<instance_data>/cogs/CogManager/cogs/`), not just `<instance_data>/cogs/`. `cog/gamoai.py` is a legacy wrapper only.

Then in Discord, as bot owner: `[p]gamoai status`, `[p]gamoai channel add #test`, `[p]gamoai chance 5`.

Enable Message Content intent on the bot application, or the cog will not see
message text.

## 3. Verification checklist

- `[p]gamoai status` reports `AI: on`, `Hindsight: ok`.
- Mentioning the bot in an allowed channel produces one reply, not two.
- A random-chance turn after the cooldown produces a reply; turns inside the
  cooldown are still buffered into Hindsight memory but do not get a reply.
- 15 passive messages in one channel flush to both banks.
- `[p]gamoai purge bank <guild> <user>` removes that bank; a fresh recall finds nothing.
- No bank or transcript is shared between two guilds.

## 4. Gotchas

- `VISION_*` can point at a separate OpenAI-compatible multimodal endpoint. Messages with inline images go there directly: memory context is still injected, but the Hermes agent loop and its tools (including `video_analyze`) are not used on those turns. Chat-only turns still go through `gamoaibot`.
- No `DISCORD_BOT_TOKEN` goes in either env file. Red owns Discord auth; the profile is not a gateway and the cog is not a standalone bot. A separate test token requires a second Red instance.
- Profiles do not sandbox the filesystem. Restrict toolsets and keep `terminal` disabled; the explicit `terminal.cwd` is defense in depth only.
- The cog ignores NSFW channels by design. Test in a non-NSFW channel.
- Hindsight banks are created lazily by retain. Deleting a bank with the purge command is a real DELETE against Hindsight; there is no undo.
- Purging already-flushed memories for a single deleted message is not implemented in v1.
