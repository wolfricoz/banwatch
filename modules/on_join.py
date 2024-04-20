import logging

from discord.ext import commands
from sqlalchemy.orm import sessionmaker


from classes.bans import Bans
from classes.configer import Configer


class Events(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Checks if user is banned"""
        bot = self.bot
        config = await Configer.get(member.guild.id, "modchannel")
        configid = int(config)
        channel = bot.get_channel(configid)
        sr = await Bans().check(self.bot, int(member.id))

        if sr is None:
            logging.info(f"{member} has no ban record")
            return
        await Bans().send_to_channel(channel, sr, int(member.id))


async def setup(bot):
    await bot.add_cog(Events(bot))
