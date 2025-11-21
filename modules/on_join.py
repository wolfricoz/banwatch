import logging

import discord
from discord.ext import commands
from discord_py_utilities.messages import send_message
from discord_py_utilities.permissions import find_first_accessible_text_channel

from classes.bans import Bans
from classes.configdata import ConfigData
from view.buttons.lookup import LookUp


class Events(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Checks if user is banned"""
        bot = self.bot
        channel = await ConfigData().get_channel(member.guild)
        sr = await Bans().get_user_bans(member.id)

        if sr is None or len(sr) < 1:
            logging.info(f"{member} has no ban record")
            return
        if channel is None:
            # await send_message(member.guild.owner, 'No mod channel set, please set one to receive banwatch notifications', error_mode='ignore')
            channel = find_first_accessible_text_channel(member.guild)
            await send_message(channel, f"No mod channel set for {member.guild.name}, unable to send banwatch notifications in this server. Please resolve this with `/config change`.",
															 error_mode="ignore")
            return
        view: LookUp = LookUp(user_id=member.id)
        await view.send_message(bot, channel, sr, member)


async def setup(bot):
    await bot.add_cog(Events(bot))
