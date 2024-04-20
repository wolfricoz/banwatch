import discord
from discord import app_commands
from discord.ext import commands
from classes.configer import Configer
from discord.app_commands import Choice




class config(commands.GroupCog, name="config"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="change", description="**CONFIG COMMAND**: Sets up the channels for the bot.")
    @app_commands.choices(option=[
        Choice(name="Mod channel", value="mod"),
    ])
    @app_commands.checks.has_permissions(manage_guild=True)
    async def crole(self, interaction: discord.Interaction, option: Choice[str], channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        match option.value:
            case "mod":
                await Configer.change(interaction.guild.id, interaction, channel.id, "modchannel")


async def setup(bot: commands.Bot):
    await bot.add_cog(config(bot))


