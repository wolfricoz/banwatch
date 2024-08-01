import logging

import discord
from discord.ext import commands

from classes.bans import Bans
from classes.configer import Configer
from view.buttons.banapproval import BanApproval


class BanEvents(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        """informs other servers an user is banned and updates banlist"""
        print('ban event')

        bot = self.bot
        logging.info("starting to update banlist and informing other servers")
        ban = await guild.fetch_ban(user)
        found = False
        await Bans().add_ban(bot, guild, user, ban.reason)
        if ban.reason is None or ban.reason in ["", "none", "Account has no avatar.", "No reason given."] or str(ban.reason).lower().startswith('[silent]') or str(ban.reason).lower().startswith('[hidden]'):
            print("silent or hidden ban/no reason, not adding to list")
            return
        channel = bot.get_channel(bot.BANCHANNEL)
        wait_id = await Bans().announce_add(guild.id, user.id, ban.reason)
        embed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({guild.owner})",
                              description=f"{ban.reason}")
        embed.set_footer(text=f"/approve_ban {wait_id}")
        checklist: list = await Configer.get_checklist()
        if checklist:
            for word in checklist:
                if word.lower() in ban.reason.lower():
                    found = True
        if not found:
            invite = await Bans().create_invite(guild)
            owner = guild.owner
            embed.set_footer(text=f"Server Invite: {invite} Server Owner: {owner} ban ID: {wait_id}")
            await Bans().check_guilds(None, bot, guild, user, embed, wait_id)
            return

        await self.verification_notification(ban, bot, guild, user)
        await channel.send(embed=embed, view=BanApproval(bot, wait_id, True))
        return

    async def verification_notification(self, ban, bot, guild, user):
        modchannel_id = await Configer.get(guild.id, "modchannel")
        modchannel = bot.get_channel(int(modchannel_id))
        supportguild = bot.get_guild(bot.SUPPORTGUILD)
        support_invite = await Bans().create_invite(supportguild)
        await modchannel.send(f"Banwatch has flagged a ban in {user}({user.id}) with the reason: `{ban.reason}` for further review. Please join the support server and open a ticket."
                              f"\n-# You can join our support server by [clicking here to join]({support_invite}). We investigate certain bans with serious accusations to prevent spreading false information.")


async def setup(bot):
    await bot.add_cog(BanEvents(bot))
