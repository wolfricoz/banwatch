from discord.ext import tasks, commands
from sqlalchemy.orm import sessionmaker



class refresher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.index = 0
        self.printer.start()

    def cog_unload(self):
        self.printer.cancel()

    @tasks.loop(hours=2)
    async def printer(self):
        """Updates banlist when user is unbanned"""
        print(f"[auto refresh]refreshing banlist")
        bot = self.bot
        newbans = {}
        for guild in bot.guilds:
            async for entry in guild.bans():
                if str(entry.user.id) in newbans:
                    if entry.reason.lower() == 'none':
                        print(f"{entry.user} has no reason, and will be removed from the list")
                    newbans[f"{entry.user.id}"][f"{guild.id}"] = {}
                    newbans[f"{entry.user.id}"][f"{guild.id}"]['reason'] = entry.reason
                    newbans[f"{entry.user.id}"]['name'] = entry.user.name
                else:
                    newbans[f"{entry.user.id}"] = {}
                    newbans[f"{entry.user.id}"][f"{guild.id}"] = {}
                    newbans[f"{entry.user.id}"][f"{guild.id}"]['reason'] = entry.reason
                    newbans[f"{entry.user.id}"]['name'] = entry.user.name
        bot.bans = newbans
        print("[auto refresh]List updated")


async def setup(bot):
    await bot.add_cog(refresher(bot))
