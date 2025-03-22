from discord.ext import commands, tasks
import logging

from classes.bans import Bans
from classes.blacklist import blacklist_check
from classes.configer import Configer
from classes.queue import queue
from classes.support.discord_tools import send_message
from classes.tasks import pending_bans
from database.databaseController import ServerDbTransactions


class Tasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_blacklist.start()
        self.check_active_servers.start()

    def cog_unload(self):
        self.check_blacklist.cancel()
        self.check_active_servers.cancel()

    @tasks.loop(hours=1)
    async def check_blacklist(self):
        if self.check_blacklist.current_loop == 0:
            return
        print(f"[blacklist check]Checking for blacklisted servers")
        dev = self.bot.get_channel(int(self.bot.DEV))
        for guild in self.bot.guilds:
            if guild.id == self.bot.SUPPORTGUILD:
                continue
            if await blacklist_check(guild, dev):
                continue

    @tasks.loop(hours=24)
    async def check_pending_bans(self):
        if self.check_pending_bans.current_loop == 0:
            return
        await pending_bans(self.bot)

    @check_pending_bans.before_loop
    async def before_check_pending_bans(self):
        await self.bot.wait_until_ready()

    @check_blacklist.before_loop
    async def before_check_blacklist(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=12)
    async def check_active_servers(self) :
        logging.info(f"Checking active servers")
        guild_ids = ServerDbTransactions().get_all()
        for guild in self.bot.guilds :
            if guild.id in guild_ids :
                guild_ids.remove(guild.id)
                ServerDbTransactions().update(guild.id, active=True)
                continue
            ServerDbTransactions().add(guild.id, guild.owner.name, guild.name, len(guild.members), "")
        for gid in guild_ids :
            ServerDbTransactions().update(gid, active=False)

    @check_active_servers.before_loop
    async def before_check_active_servers(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Tasks(bot))
