#!/bin/sh
# Test Red instance for GamoAI. Token lives in Red's own instance config,
# not in this file. Single canonical cog env file: cog/.env.
set -a
. <LOCAL_HOME>/GamoAICog/cog/.env
set +a
exec <LOCAL_HOME>/GamoAICog/.venv/bin/redbot gamoai-test --load-cogs gamoaicog "$@"
