"""GamoAI Red cog package (installable via Red's Downloader cog)."""

__version__ = "0.1.0"


async def setup(bot) -> None:  # noqa: ANN001 - Red's bot type
    from .cog import GamoAICog

    await bot.add_cog(GamoAICog(bot))
