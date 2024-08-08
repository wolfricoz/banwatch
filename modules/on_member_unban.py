import logging

from discord.ext import commands

from classes.bans import Bans


class UnBanEvents(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_member_unban")
    async def on_member_unban(self, guild, user):
        """Updates banlist when user is unbanned"""
        logging.info(f"{guild}: unbanned {user}, refreshing banlist")
        unique_id = user.id + guild.id
        await Bans().update(self.bot)
        await Bans().revoke_bans(self.bot, unique_id, "User was unbanned by the server.")
        logging.info("List updated")


async def setup(bot):
    await bot.add_cog(UnBanEvents(bot))
