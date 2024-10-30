import discord
from discord.ext import commands
from discord.ui import View

from classes.configer import Configer
from database.databaseController import AppealsDbTransactions


class AppealButtons(View):
    bot = None

    def __init__(self, bot, user):
        super().__init__(timeout=None)
        self.bot: commands.Bot = bot
        self.user: discord.Member = user

    @discord.ui.button(label="Unban", style=discord.ButtonStyle.success, custom_id="approve_appeal")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if self.bot is None or self.user is None:
            await interaction.followup.send("Error: The bot has restarted, the data of this button was lost", ephemeral=True)
            return
        await self.disable_buttons(interaction)
        await interaction.guild.unban(self.user, reason="Appeal approved")
        AppealsDbTransactions().change_status(self.user.id + interaction.guild.id, 'approved')
        await interaction.followup.send("Appeal approved, user unbanned", ephemeral=True)
        await self.user.send(f"Your appeal has been approved, you have been unbanned from {interaction.guild.name}")

    @discord.ui.button(label="Decline Appeal", style=discord.ButtonStyle.danger, custom_id="deny_appeal")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if self.bot is None or self.user is None:
            await interaction.followup.send("Error: The bot has restarted, the data of this button was lost", ephemeral=True)
            return
        await self.disable_buttons(interaction)
        AppealsDbTransactions().change_status(self.user.id + interaction.guild.id, 'denied')
        await interaction.followup.send("Appeal denied", ephemeral=True)
        await self.user.send(f"Your appeal has been denied in {interaction.guild.name}")

    async def disable_buttons(self, interaction: discord.Interaction):
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
