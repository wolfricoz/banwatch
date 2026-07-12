import logging

from discord.ext import commands, tasks

from classes.bans import Bans
from database.transactions.BanTransactions import BanTransactions


class Refresher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.index = 0
        self.ban_update_task.start()

    def cog_unload(self):
        self.ban_update_task.cancel()

    # TODO: [BUG/dead code] ban_update_task is DEFINED TWICE in this class. In Python the second
    #  definition (the @tasks.loop(minutes=10) one below) completely replaces this @tasks.loop(hours=2)
    #  method - so this 2-hour full refresh, including `await Bans().update(bot)`, NEVER RUNS. Only the
    #  10-minute cache rebuild is active. If the full banlist refresh is still wanted, rename one of the
    #  two loops (e.g. full_refresh_task) and register/cancel both in cog_load/cog_unload.
    @tasks.loop(hours=2)
    async def ban_update_task(self):
        """Updates banlist when user is unbanned"""
        if self.ban_update_task.current_loop == 0:
            return
        logging.info(f"[auto refresh]refreshing banlist")
        bot = self.bot
        await Bans().update(bot)
        await BanTransactions().populate_cache()
        logging.info(f"[auto refresh]Bans Updated")

    @tasks.loop(minutes=10)
    async def populate_cache_task(self) :
        await self.bot.wait_until_ready()
        logging.info("Rebuilding cache")
        await BanTransactions().populate_cache()
        logging.info("Finished building cache")


    @ban_update_task.before_loop
    async def before_ban_update_task(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Refresher(bot))
