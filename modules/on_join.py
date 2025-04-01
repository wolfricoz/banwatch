import logging

from discord.ext import commands

from classes.bans import Bans
from classes.configdata import ConfigData
from classes.configer import Configer
from view.buttons.lookup import LookUp


class Events(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Checks if user is banned"""
        bot = self.bot
        config = ConfigData().get_key_or_none(member.guild.id, "modchannel")
        if config is None:
            member.guild.owner.send(f"No mod channel set, please set one to receive banwatch notifications. You can do this by using the command `/config change`.")
        configid = int(config)
        channel = bot.get_channel(configid)
        sr = await Bans().get_user_bans(member.id)

        if sr is None or len(sr) < 1:
            logging.info(f"{member} has no ban record")
            return
        if channel is None:
            await member.guild.owner.send('No mod channel set, please set one to receive banwatch notifications')
            return
        view: LookUp = LookUp(user_id=member.id)
        await view.send_message(bot, channel, sr, member)


async def setup(bot):
    await bot.add_cog(Events(bot))
