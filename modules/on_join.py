import logging

from discord.ext import commands
from sqlalchemy.orm import sessionmaker


from classes.bans import Bans, DatabaseBans
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
        sr = await DatabaseBans().get_user_bans(member.id)
        print(sr)

        if sr is None or len(sr) < 1:
            logging.info(f"{member} has no ban record")
            return
        if channel is None:
            await member.guild.owner.send('No mod channel set, please set one to receive banwatch notifications')
        await Bans().send_to_channel(bot, channel, sr, member, excess=False)


async def setup(bot):
    await bot.add_cog(Events(bot))
