import logging

import discord
from discord.ui import View

from classes.bans import Bans
from classes.configer import Configer
from classes.queue import queue


class BanApproval(View):
    bot = None

    def __init__(self, bot, wait_id, create_thread = False):
        super().__init__(timeout=None)
        self.bot = bot
        self.wait_id = wait_id
        self.create_thread = create_thread

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, custom_id="approve_broadcast")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if self.bot is None or self.wait_id is None:
            await interaction.followup.send("Error: The bot has restarted, the data of this button was lost", ephemeral=True)
            return
        guildid, userid, reason = await Bans().announce_retrieve(self.wait_id)
        if guildid is None or userid is None or reason is None:
            await interaction.followup.send("Waitlist ERROR", ephemeral=True)
            return
        guild = self.bot.get_guild(guildid)
        owner = guild.owner
        user = await self.bot.fetch_user(userid)
        banembed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({owner})",
                                 description=f"{reason}")
        invite = await Bans().create_invite(guild)
        banembed.set_footer(text=f"Server Invite: {invite} Server Owner: {owner} Banned userid: {user.id} ")
        await interaction.followup.send("Approved", ephemeral=True)
        await Bans().check_guilds(interaction, self.bot, guild, user, banembed, self.wait_id, self.create_thread)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, custom_id="deny_broadcast")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        if self.bot is None or self.wait_id is None:
            await interaction.followup.send("Error: The bot has restarted, the data of this button was lost", ephemeral=True)
            return
        guildid, userid, reason = await Bans().announce_retrieve(self.wait_id)
        if guildid is None or userid is None or reason is None:
            await interaction.followup.send("Waitlist ERROR", ephemeral=True)
            return
        guild = self.bot.get_guild(guildid)
        owner = guild.owner
        user = await self.bot.fetch_user(userid)
        denial_channel = self.bot.get_channel(self.bot.DENIALCHANNEL)
        banembed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({owner})",
                                 description=f"{reason}")
        await interaction.followup.send("Denied", ephemeral=True)
        await interaction.message.delete()
        banembed.set_footer(text="Denied")
        await denial_channel.send(embed=banembed)
