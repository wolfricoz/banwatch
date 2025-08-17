import asyncio
import logging
from datetime import datetime, timedelta

from discord.ext import commands, tasks

from database.databaseController import BanDbTransactions, ServerDbTransactions


class DatabaseTasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.delete_old_bans.start()

    def cog_unload(self):
        self.delete_old_bans.cancel()

    @tasks.loop(hours=2)
    async def delete_old_bans(self):
        bans = BanDbTransactions().get_deleted_bans()
        servers = ServerDbTransactions().get_deleted()
        logging.info(f"Checking soft-deleted entries for removal")
        for ban in bans:
            await asyncio.sleep(0.1)
            if ban.deleted_at is None:
                continue
            if ban.deleted_at < datetime.now() - timedelta(days=30):
                BanDbTransactions().delete_permanent(ban)
        for server in servers:
            if server.deleted_at < datetime.now() - timedelta(days=30):
                try:
                    ServerDbTransactions().delete_permanent(server)
                except Exception as e:
                    logging.error(f"Failed to delete permanent for {server}", exc_info=True)

    @delete_old_bans.before_loop
    async def before_queue(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(DatabaseTasks(bot))
