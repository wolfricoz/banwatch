from discord.ext import tasks, commands

from classes.bans import Bans


class refresher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.index = 0
        self.ban_update_task.start()

    def cog_unload(self):
        self.ban_update_task.cancel()

    @tasks.loop(hours=2)
    async def ban_update_task(self):
        """Updates banlist when user is unbanned"""
        print(f"[auto refresh]refreshing banlist")
        bot = self.bot
        await Bans().update(bot, override=True)
        print(f"[auto refresh]Bans Updated")


async def setup(bot):
    await bot.add_cog(refresher(bot))
