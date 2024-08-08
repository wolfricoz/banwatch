from discord.ext import commands, tasks

from classes.queue import queue


class queueTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queue.start()

    def cog_unload(self):
        self.queue.cancel()

    @tasks.loop(seconds=1)
    async def queue(self):
        await queue().start()



async def setup(bot):
    await bot.add_cog(queueTask(bot))
