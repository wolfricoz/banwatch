import logging

import discord
from discord.app_commands import guilds
from discord.ui import View

from classes.bans import Bans
from classes.configer import Configer
from classes.queue import queue
from classes.support.discord_tools import send_message, send_response
from database.databaseController import BanDbTransactions
from view.modals.inputmodal import send_modal


class BanApproval(View):
    bot = None

    def __init__(self, bot, wait_id, create_thread = False, silent = False):
        super().__init__(timeout=None)
        self.bot = bot
        self.wait_id = wait_id
        self.create_thread = create_thread
        self.silent = silent

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.success, custom_id="verify_ban")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if self.bot is None or self.wait_id is None:
            await interaction.followup.send("Error: The bot has restarted, the data of this button was lost", ephemeral=True)
            return
        ban_entry = BanDbTransactions().get(self.wait_id, override=True)
        if ban_entry is None:
            await interaction.followup.send("Ban not found", ephemeral=True)
            return
        # noinspection PyTypeChecker,PydanticTypeChecker
        if len(ban_entry.proof) < 1:
            await interaction.followup.send("No evidence found, please add evidence and try again", ephemeral=True)
            return
        guildid = ban_entry.gid
        userid = ban_entry.uid
        reason = ban_entry.reason
        guild = self.bot.get_guild(guildid)
        owner = guild.owner
        user = await self.bot.fetch_user(userid)
        banembed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({owner})",
                                 description=f"{reason}")
        invite = await Bans().create_invite(guild)
        banembed.set_footer(text=f"Server Invite: {invite} Server Owner: {owner} ban ID: {self.wait_id}. ")
        interaction.message.embeds[0].set_footer(text=f"Verified by {interaction.user}")
        await interaction.message.edit(embed=interaction.message.embeds[0])
        if self.silent:
            return
        await Bans().check_guilds(None, self.bot, guild, user, banembed, self.wait_id, self.create_thread, verified=True)

    @discord.ui.button(label="approve", style=discord.ButtonStyle.success, custom_id="approve_ban")
    async def approve_no_proof(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if self.bot is None or self.wait_id is None:
            await interaction.followup.send("Error: The bot has restarted, the data of this button was lost", ephemeral=True)
            return
        ban_entry = BanDbTransactions().get(self.wait_id)
        if ban_entry is None:
            await interaction.followup.send("Ban not found", ephemeral=True)
            return
        guildid = ban_entry.gid
        userid = ban_entry.uid
        reason = ban_entry.reason
        guild = self.bot.get_guild(guildid)
        owner = guild.owner
        user = await self.bot.fetch_user(userid)
        banembed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({owner})",
                                 description=f"{reason}")
        invite = await Bans().create_invite(guild)
        banembed.set_footer(text=f"Server Invite: {invite} Server Owner: {owner} ban ID: {self.wait_id} ")
        await interaction.followup.send(f"Approved without proof by {interaction.user.mention}! {'Silent option was true, ban not broadcast' if self.silent else ''}", ephemeral=False)
        interaction.message.embeds[0].set_footer(text=f"Verified by {interaction.user}")
        await interaction.message.edit(embed=interaction.message.embeds[0])
        if self.silent:
            return
        await Bans().check_guilds(None, self.bot, guild, user, banembed, self.wait_id, False)

    @discord.ui.button(label="request evidence", style=discord.ButtonStyle.danger, custom_id="custom_ID")
    async def evidence(self, interaction: discord.Interaction, button: discord.ui.Button):
        reason = await send_modal(interaction, confirmation="Thank you for providing a reason", title="What evidence do we require?")
        if not reason:
            return
        ban_entry = BanDbTransactions().get(self.wait_id, override=True)
        if ban_entry is None:
            return await send_response(interaction, "Ban not found")
        guild: discord.Guild = interaction.client.get_guild(ban_entry.gid)
        user:discord.User = await interaction.client.fetch_user(ban_entry.uid)
        modchannel = guild.get_channel(await Configer.get(guild.id, "modchannel"))

        content = f"The banwatch team requests that you add more evidence to user {user}({user.id}), you can do this by joining our support guild or by using `/evidence add user:{user.id}`."
        embed = discord.Embed(title=f"Evidence request for ban {ban_entry.ban_id}", description=content)
        embed.add_field(name=f"Request reason", value=reason)
        await send_message(modchannel, embed=embed)
        await send_response(interaction, f"Server has been notified with reason:\n{reason}")



    @discord.ui.button(label="Hide Ban", style=discord.ButtonStyle.danger, custom_id="deny_broadcast")
    async def Hide(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        if self.bot is None or self.wait_id is None:
            await interaction.followup.send("Error: The bot has restarted, the data of this button was lost", ephemeral=True)
            return
        ban_entry = BanDbTransactions().get(self.wait_id)
        if ban_entry is None:
            await interaction.followup.send("Ban not found", ephemeral=True)
            return
        guildid = ban_entry.gid
        userid = ban_entry.uid
        reason = ban_entry.reason
        guild = self.bot.get_guild(guildid)
        owner = guild.owner
        user = await self.bot.fetch_user(userid)
        denial_channel = self.bot.get_channel(self.bot.DENIALCHANNEL)
        banembed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({owner})",
                                 description=f"{reason}")
        await interaction.followup.send("Denied", ephemeral=True)
        await interaction.message.delete()
        banembed.set_footer(text="Denied")
        BanDbTransactions().update(self.wait_id, approved=True, hidden=True)
        await denial_channel.send(embed=banembed)

