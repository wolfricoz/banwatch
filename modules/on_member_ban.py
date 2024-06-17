import logging
from datetime import datetime

import discord
from discord.ext import commands

from classes.bans import Bans
from view.buttons.banapproval import BanApproval


class BanEvents(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        """informs other servers an user is banned and updates banlist"""
        print('ban event')
        bot = self.bot
        # sleep = random.randint(60, 600)
        # logging.info(f"{guild}: banned {user}, adding to banlist in {sleep} seconds")
        # await asyncio.sleep(sleep)
        logging.info("starting to update banlist and informing other servers")
        ban = await guild.fetch_ban(user)
        await Bans().add_ban(bot, guild, user, ban.reason)
        channel = bot.get_channel(bot.BANCHANNEL)

        embed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({guild.owner})",
                              description=f"{ban.reason}")
        embed.set_footer(text=f"{datetime.now()}")
        await channel.send(embed=embed, view=BanApproval(bot, guild, user, ban, 5))

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        """Updates banlist when user is unbanned"""
        logging.info(f"{guild}: unbanned {user}, refreshing banlist")
        await Bans().update(self.bot)
        logging.info("List updated")


async def setup(bot):
    await bot.add_cog(BanEvents(bot))