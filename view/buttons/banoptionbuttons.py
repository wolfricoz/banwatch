import os

import discord
from discord.ui import View, button

from classes.bans import DatabaseBans, Bans
from classes.configer import Configer
from classes.queue import queue
from classes.support.discord_tools import send_message
from database.databaseController import ServerDbTransactions
from view.buttons.banapproval import BanApproval


class BanOptionButtons(View):

    def __init__(self):
        super().__init__(timeout=None)

    async def get_data(self, interaction: discord.Interaction):
        """Gets the user data from the embed"""
        ids = interaction.message.embeds[0].footer.text.split("-")
        guild = interaction.guild
        user = interaction.client.get_user(int(ids[1]))
        ban = await guild.fetch_ban(user)
        return guild, user, ban

    @button(label="Share", custom_id="share", style=discord.ButtonStyle.success)
    async def share(self, interaction: discord.Interaction, button: button):
        await self.process(interaction)

    @button(label="Share with proof", custom_id="share_with_proof", style=discord.ButtonStyle.success)
    async def share_with_proof(self, interaction: discord.Interaction, button: button):
        guild, user, ban = await self.get_data(interaction)
        checklist_check = self.check_checklisted_words(ban)

        pass

    @button(label="Silent", custom_id="silent", style=discord.ButtonStyle.primary)
    async def silent(self, interaction: discord.Interaction, button: button):
        guild, user, ban = await self.get_data(interaction)
        checklist_check = self.check_checklisted_words(ban)

        pass

    @button(label="Hide", custom_id="hide", style=discord.ButtonStyle.danger)
    async def hidden(self, interaction: discord.Interaction, button: button):
        guild, user, ban = await self.get_data(interaction)
        checklist_check = self.check_checklisted_words(ban)
        pass

    async def process(self, interaction, hidden=False, silent=False, proof=None):
        guild, user, ban = await self.get_data(interaction)
        guild_db = ServerDbTransactions().get(guild.id)
        wait_id = guild.id + user.id
        checklist_check = await self.check_checklisted_words(ban)
        staff_member: discord.User = await self.get_staff_member(guild, user)
        message: discord.Message = interaction.message
        wait_id = await Bans().announce_add(guild.id, user.id, ban.reason)
        if checklist_check:
            channel = interaction.client.get_channel(int(os.getenv("BANS")))
            await DatabaseBans().add_ban(user.id, guild.id, ban.reason, staff_member.name, approved=False)
            await self.status(interaction.client, guild, user, "waiting_approval", ban.reason, word=checklist_check, message=message)
            embed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({guild.owner})",
                                  description=f"{ban.reason}")
            embed.set_footer(text=f"invite: {guild_db.invite} To approve it manually: /approve_ban {wait_id} ")
            await send_message(channel, embed=embed, view=BanApproval(interaction.client, wait_id, True))

        await DatabaseBans().add_ban(user.id, guild.id, ban.reason, staff_member.name)
        embed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({guild.owner})",
                              description=f"{ban.reason}")
        embed.set_footer(text=f"Server Invite: {guild_db.invite} Staff member: {staff_member} ban ID: {wait_id}")
        await Bans().check_guilds(interaction, interaction.client, guild, user, embed, wait_id)
        await self.status(interaction.client, guild, user)


    async def check_checklisted_words(self, ban):
        found = None
        checklist: list = await Configer.get_checklist()
        if checklist:
            for word in checklist:
                if word.lower() in ban.reason.lower():
                    found = word
        return found

    async def get_staff_member(self, guild, user):
        async for entry in guild.audit_logs(limit=100, action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                if entry.user.bot:
                    return guild.owner
                return entry.user

    async def verification_notification(self, banreason, bot, guild, user, word, message: discord.Message = None):
        modchannel_id = await Configer.get(guild.id, "modchannel")
        modchannel = bot.get_channel(int(modchannel_id))
        supportguild = bot.get_guild(bot.SUPPORTGUILD)
        support_invite = await Bans().create_invite(supportguild)
        verembed = discord.Embed(title=f"ban for {user}({user.id}) was flagged for review",
                                 description=f"{banreason}\n\n"
                                             f"Flagged word: {word}. We review bans with serious accusations to ensure they are legitimate.")
        verembed.set_footer(text=f"Please supply evidence by using the /evidence add commmand, or by joining our support server (18+).")
        if message:
            await message.edit(content=f"-# You can join our support server by [clicking here to join]({support_invite}).", embed=verembed, view=None)
            return
        await send_message(modchannel, f"-# You can join our support server by [clicking here to join]({support_invite}).", embed=verembed)

    async def status(self, bot, guild, user: discord.User, status="queued", banreason=None, word=None, message=None):
        """informs user is the ban has been approved or is in queue"""
        modchannel = await Configer.get(guild.id, "modchannel")
        channel = bot.get_channel(int(modchannel))
        if status == "waiting_approval":
            await self.verification_notification(banreason, bot, guild, user, word=word, message=message)
            return
        message: discord.Message = await channel.send(f"Your ban for {user.mention} is currently: {status}.")
        queue().add(message.edit(content=f"Your ban for {user.mention} has been successfully broadcasted to other servers."))
