import logging

from discord.ext import commands, tasks

from classes.bans import Bans
from database.transactions.BanTransactions import BanDbTransactions


class Refresher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.index = 0
        self.ban_update_task.start()

    def cog_unload(self):
        self.ban_update_task.cancel()

    @tasks.loop(hours=2)
    async def ban_update_task(self):
        """Updates banlist when user is unbanned"""
        if self.ban_update_task.current_loop == 0:
            return
        logging.info(f"[auto refresh]refreshing banlist")
        bot = self.bot
        await Bans().update(bot)
        BanDbTransactions().populate_cache()
        logging.info(f"[auto refresh]Bans Updated")

    @tasks.loop(minutes=10)
    async def ban_update_task(self) :
        await self.bot.wait_until_ready()
        logging.info("Rebuilding cache")
        BanDbTransactions().populate_cache()
        logging.info("Finished building cache")


    @ban_update_task.before_loop
    async def before_ban_update_task(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Refresher(bot))
