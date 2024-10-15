from discord.ext import commands, tasks

from classes.queue import queue


class queueTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queue.start()

    def cog_unload(self):
        self.queue.cancel()

    @tasks.loop(seconds=0.3)
    async def queue(self):
        await queue().start()

    @queue.before_loop
    async def before_queue(self):
        await self.bot.wait_until_ready()



async def setup(bot):
    await bot.add_cog(queueTask(bot))
