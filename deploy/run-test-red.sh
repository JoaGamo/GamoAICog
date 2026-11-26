#!/bin/sh
# Local test Red instance for GamoAI. The token lives in Red's own instance
# config, not in this file. Env comes from the single canonical cog env file.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO=$(dirname -- "$HERE")
set -a
. "$REPO/cog/.env"
set +a
exec "$REPO/.venv/bin/redbot" gamoai-test --load-cogs gamoaicog "$@"
