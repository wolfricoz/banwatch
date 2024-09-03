import logging

import discord
from discord.ext import commands

from classes.bans import Bans
from classes.configer import Configer
from classes.queue import queue
from classes.support.discord_tools import send_message
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
        found = None
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
                    found = word
        if not found:
            invite = await Bans().create_invite(guild)
            owner = guild.owner
            embed.set_footer(text=f"Server Invite: {invite} Server Owner: {owner} ban ID: {wait_id}")
            print(embed.to_dict())
            await Bans().check_guilds(None, bot, guild, user, embed, wait_id)
            await self.status(bot, guild, user)
            return

        await self.status(bot, guild, user, "waiting_approval", ban.reason, word=found)
        await send_message(channel, embed=embed, view=BanApproval(bot, wait_id, True))
        return

    async def verification_notification(self, banreason, bot, guild, user, word):
        modchannel_id = await Configer.get(guild.id, "modchannel")
        modchannel = bot.get_channel(int(modchannel_id))
        supportguild = bot.get_guild(bot.SUPPORTGUILD)
        support_invite = await Bans().create_invite(supportguild)
        verembed = discord.Embed(title=f"ban for {user}({user.id}) was flagged for review",
                                 description=f"{banreason}\n\n"
                                             f"Flagged word: {word}. We review bans with serious accusations to ensure they are legitimate.")
        verembed.set_footer(text=f"Please supply evidence if you have any to the support server or to the dev: ricostryker")
        await send_message(modchannel, f"-# You can join our support server by [clicking here to join]({support_invite}).", embed=verembed)

    async def status(self, bot, guild, user: discord.User, status="queued", banreason=None, word=None):
        """informs user is the ban has been approved or is in queue"""
        modchannel = await Configer.get(guild.id, "modchannel")
        channel = bot.get_channel(int(modchannel))
        if status == "waiting_approval":
            await self.verification_notification(banreason, bot, guild, user, word=word)
            return
        message: discord.Message = await channel.send(f"Your ban for {user.mention} is currently: {status}.")
        queue().add(message.edit(content=f"Your ban for {user.mention} has been successfully broadcasted to other servers."), priority=0)


async def setup(bot):
    await bot.add_cog(BanEvents(bot))
