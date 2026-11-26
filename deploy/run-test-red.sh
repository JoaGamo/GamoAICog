#!/bin/sh
# Test Red instance for GamoAI. Token lives in Red's own instance config,
# not in this file. Env values come from the gitignored .env.test-red.
set -a
. <LOCAL_HOME>/GamoAICog/deploy/.env.test-red
set +a
exec <LOCAL_HOME>/GamoAICog/.venv/bin/redbot gamoai-test "$@"
