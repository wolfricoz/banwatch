import asyncio
import os

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from sqlalchemy.testing.plugin.plugin_base import logging

from classes.access import AccessControl
from classes.bans import Bans
from classes.configer import Configer
from classes.queue import queue
from classes.support.discord_tools import send_response, send_message, get_all_threads
from classes.tasks import pending_bans
from database.databaseController import StaffDbTransactions, BanDbTransactions, ServerDbTransactions
from view.modals.inputmodal import send_modal

OWNER = int(os.getenv("OWNER"))
GUILD = int(os.getenv("GUILD"))


def in_guild():
    async def predicate(interaction: discord.Interaction):
        if interaction.guild is None:
            return False
        if interaction.guild.id != GUILD:
            return False
        if interaction.user.id != OWNER:
            return False
        return True

    return app_commands.check(predicate)


SUPPORT_GUILD = discord.Object(id=GUILD)


@app_commands.guild_only()
@app_commands.guilds(SUPPORT_GUILD)
class Staff(commands.GroupCog, name="staff"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot



async def setup(bot: commands.Bot):
    await bot.add_cog(Staff(bot))
