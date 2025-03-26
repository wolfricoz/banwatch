import discord
from discord import app_commands
from discord.ext import commands

from classes.configdata import ConfigData
from classes.configer import Configer
from discord.app_commands import Choice

from classes.support.discord_tools import send_response
from database.databaseController import ServerDbTransactions


class config(commands.GroupCog, name="config"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="change", description="[CONFIG COMMAND] Sets up the channels for the bot.")
    @app_commands.choices(option=[
        Choice(name="Mod channel", value="mod"),
    ])
    @app_commands.checks.has_permissions(manage_guild=True)
    async def crole(self, interaction: discord.Interaction, option: Choice[str], channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        match option.value:
            case "mod":
                await ConfigData().add_key(interaction, "modchannel", channel.id)

    @app_commands.command(name="appeals", description="[CONFIG COMMAND] turn on/off ban appeals")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def command(self, interaction: discord.Interaction, allow: bool):
        await interaction.response.defer(ephemeral=True)
        await ConfigData().add_key(interaction, "allow_appeals", allow)

    @app_commands.command(name="visibility", description="[Config Command] Allows you to hide all bans from banwatch")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def command(self, interaction: discord.Interaction, hide: bool):
        ServerDbTransactions().update(interaction.guild.id, hidden=hide)
        await send_response(interaction, f"Your server's visibility has ben set to: {'hidden' if hide is True else 'Visible'}\n\n"
                                         f"Your bans may temporarily still be available in the checkall cache, which is reloaded every 10 minutes")


async def setup(bot: commands.Bot):
    await bot.add_cog(config(bot))


