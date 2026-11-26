"""Red cog entry point.

Copy this file and the gamoaicog/ package into Red's cogs/ directory.
"""

from __future__ import annotations

from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional; real env vars still work
    def load_dotenv(*_args, **_kwargs) -> bool:
        return False


# Load cog/.env when present; real environment variables still win.
load_dotenv(Path(__file__).resolve().parent / ".env", override=False)


async def setup(bot) -> None:  # noqa: ANN001 - Red's bot type
    from gamoaicog.cog import setup as setup_cog

    await setup_cog(bot)
