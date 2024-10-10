import logging
from datetime import datetime, timedelta

from discord.ext import commands, tasks

from classes.queue import queue
from database.databaseController import BanDbTransactions


class DatabaseTasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.delete_old_bans.start()

    def cog_unload(self):
        self.delete_old_bans.cancel()

    @tasks.loop(hours=2)
    async def delete_old_bans(self):
        bans = BanDbTransactions().get_deleted_bans()
        for ban in bans:
            if ban.deleted_at < datetime.now() - timedelta(days=7):
                queue().add(self.delete(ban), 0)

    async def delete(self, ban):
        result = BanDbTransactions().delete_permanent(ban.ban_id)
        if not result:
            logging.error(f"Failed to delete {ban.ban_id}")
            return
        logging.info(f"Deleted {ban.ban_id}")

    @delete_old_bans.before_loop
    async def before_queue(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(DatabaseTasks(bot))
