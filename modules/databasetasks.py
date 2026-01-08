import asyncio
import logging
from datetime import UTC, datetime, timedelta

from discord.ext import commands, tasks

from database.transactions.BanTransactions import BanTransactions
from database.transactions.ServerTransactions import ServerTransactions


class DatabaseTasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.delete_old_bans.start()

    def cog_unload(self):
        self.delete_old_bans.cancel()

    @tasks.loop(hours=2)
    async def delete_old_bans(self):
        bans = BanTransactions().get_deleted_bans()
        servers = ServerTransactions().get_deleted()
        logging.info(f"Checking soft-deleted entries for removal")
        for ban in bans:
            await asyncio.sleep(0.1)
            if ban.deleted_at is None:
                continue
            if ban.deleted_at.replace(tzinfo=UTC)  < datetime.now(tz=UTC) - timedelta(days=30):
                BanTransactions().delete_permanent(ban)
        for server in servers:
            if server.deleted_at.replace(tzinfo=UTC) < datetime.now() - timedelta(days=30):
                try:
                    ServerTransactions().delete_permanent(server)
                except Exception as e:
                    logging.error(f"Failed to delete permanent for {server}", exc_info=True)

    @delete_old_bans.before_loop
    async def before_queue(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(DatabaseTasks(bot))
