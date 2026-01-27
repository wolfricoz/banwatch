import logging

import discord
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
        try:
            async for entry in guild.audit_logs(action=discord.AuditLogAction.unban, limit=1):
                if entry.target.id == user.id:
                    reason = entry.reason
                    break
            else:
                reason = "MemberLookup was unbanned by the server with no reason provided"
        except discord.Forbidden:
            reason = "MemberLookup was unbanned by the server with no reason provided"
            await guild.owner.send(f"Please give me the permission to view audit logs to get the reason for the unban of {user}")
        await Bans().revoke_bans(self.bot, unique_id, reason)
        await Bans().delete_ban(user.id, guild.id)
        # await Bans().update(self.bot)
        logging.info("List updated")


async def setup(bot):
    await bot.add_cog(UnBanEvents(bot))
