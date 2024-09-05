from discord.ext import tasks, commands

from classes.bans import Bans


class refresher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.index = 0
        self.ban_update_task.start()

    def cog_unload(self):
        self.ban_update_task.cancel()

    @tasks.loop(hours=4)
    async def ban_update_task(self):
        """Updates banlist when user is unbanned"""
        if self.ban_update_task.current_loop == 0:
            return
        print(f"[auto refresh]refreshing banlist")
        bot = self.bot
        await Bans().update(bot)
        print(f"[auto refresh]Bans Updated")

    @ban_update_task.before_loop
    async def before_ban_update_task(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(refresher(bot))
