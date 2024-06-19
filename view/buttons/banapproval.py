import logging

import discord
from discord.ui import View

from classes.configer import Configer
from classes.queue import queue


class BanApproval(View):
    bot = None

    def __init__(self, bot, guild, user, ban):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild: discord.Guild = guild
        self.user = user
        self.ban = ban

    async def inform_server(self, guilds, banembed):
        config = await Configer.get(guilds.id, "modchannel")
        modchannel = self.bot.get_channel(int(config))
        await modchannel.send(embed=banembed)

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, custom_id="approve_broadcast")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if self.bot is None or self.guild is None or self.user is None or self.ban is None:
            await interaction.followup.send("Error: The bot has restarted, the data of this button was lost", ephemeral=True)
            return
        owner = self.guild.owner
        guild = self.guild
        user = self.user
        if self.guild.owner is None:
            owner = 'No owner'

        approved_channel = self.bot.get_channel(self.bot.APPROVALCHANNEL)
        banembed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({owner})",
                                 description=f"{self.ban.reason}")
        try:
            config = await Configer.get(self.guild.id, "modchannel")
            invite = await self.guild.get_channel(config).create_invite()
        except discord.Forbidden:
            invite = 'No permission'
        except Exception as e:
            invite = f'No permission/Error'
            logging.error(f"Error creating invite: {e}")
        banembed.set_footer(text=f"Server Invite: {invite} Server Owner: {owner} Banned userid: {user.id} ")
        await interaction.followup.send("Approved", ephemeral=True)
        for guilds in self.bot.guilds:
            if guilds.id == self.guild.id:
                continue
            if self.user in guilds.members:
                queue().add(self.inform_server(guilds, banembed))

        await interaction.message.delete()
        await approved_channel.send(embed=banembed)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, custom_id="deny_broadcast")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if self.bot is None or self.guild is None or self.user is None or self.ban is None:
            await interaction.followup.send("Error: The bot has restarted, the data of this button was lost", ephemeral=True)
            return
        denial_channel = self.bot.get_channel(self.bot.DENIALCHANNEL)
        banembed = discord.Embed(title=f"{self.user} ({self.user.id}) was banned in {self.guild}({self.guild.owner})",
                                 description=f"{self.ban.reason}")
        await interaction.followup.send("Denied", ephemeral=True)
        await interaction.message.delete()
        banembed.set_footer(text="Denied")
        await denial_channel.send(embed=banembed)
