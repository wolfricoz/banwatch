import os
import time
from abc import ABC

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.orm import sessionmaker

from classes.bans import Bans





class Utility(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command()
    async def support(self, interaction: discord.Interaction):
        await interaction.response.send_message("If you are in need of support, please read our documentation at https://wolfricoz.github.io/banwatch/! You can find our discord link in the documentation. If you still need help, please join our discord server and ask in the support channel.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))

