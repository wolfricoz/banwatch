from discord.ext import commands, tasks
from sqlalchemy.testing.plugin.plugin_base import logging

from classes.blacklist import blacklist_check
from classes.configer import Configer
from classes.queue import queue
from classes.support.discord_tools import send_message


class BlacklistTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_blacklist.start()

    def cog_unload(self):
        self.check_blacklist.cancel()

    @tasks.loop(hours=12)
    async def check_blacklist(self):
        dev = self.bot.get_channel(int(self.bot.DEV))
        for guild in self.bot.guilds:
            if guild.id == self.bot.SUPPORTGUILD:
                continue
            if await blacklist_check(guild, dev):
                continue




async def setup(bot):
    await bot.add_cog(BlacklistTask(bot))
