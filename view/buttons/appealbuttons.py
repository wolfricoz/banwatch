import discord
from discord.ext import commands
from discord.ui import View
from discord_py_utilities.messages import await_message, send_message

from classes.configer import Configer
from database.databaseController import AppealMsgTransactions, AppealsDbTransactions, BanDbTransactions
from view.modals.inputmodal import InputModal, send_modal


class AppealButtons(View) :
	bot = None

	def __init__(self) :
		super().__init__(timeout=None)

	@discord.ui.button(label="Change Status", style=discord.ButtonStyle.success, custom_id="ChangeStatus")
	async def approve(self, interaction: discord.Interaction, button: discord.ui.Button) :
		await interaction.response.defer(ephemeral=True)
		await self.load_data(interaction)
		if self.bot is None or self.user is None :
			await interaction.followup.send("Error: The bot has restarted, the data of this button was lost", ephemeral=True)
			return
		await self.disable_buttons(interaction)
		await interaction.guild.unban(self.user, reason="Appeal approved")
		AppealsDbTransactions().change_status(self.ban_id, 'approved')
		await interaction.followup.send("Appeal approved, user unbanned", ephemeral=True)
		await self.user.send(f"Your appeal has been approved, you have been unbanned from {interaction.guild.name}")

	@discord.ui.button(label="Respond", style=discord.ButtonStyle.danger, custom_id="Respond")
	async def respond(self, interaction: discord.Interaction, button: discord.ui.Button) :
		await self.load_data(interaction)
		appeal = AppealsDbTransactions().get(self.ban_id)
		response = await send_modal(interaction, "Your response will be delivered!", "What's your message?", 2000)
		title = f"Response from {interaction.guild.name} for ban id: {self.ban_id}"
		await self.send_embed(interaction, title, response)
		AppealMsgTransactions.add(response, interaction.guild.id, self.user.id, appeal.id)

	async def disable_buttons(self, interaction: discord.Interaction) :
		for child in self.children :
			child.disabled = True
		await interaction.message.edit(view=self)

	async def send_embed(self, interaction: discord.Interaction, title, content):
		embed = discord.Embed(title=title, color=discord.Color.green(), description=content)
		embed.set_footer(text=self.ban_id)
		try:
			await send_message(self.user, " ", embed=embed)
		except discord.Forbidden:
			await send_message(interaction.channel, f"Unable to send message to {self.user.name}, DMs are closed.")


	async def load_data(self, interaction: discord.Interaction):
		self.bot = interaction.client
		self.ban_id = interaction.message.embeds[0].footer.text
		ban = BanDbTransactions().get(self.ban_id, override=True)
		self.user = self.bot.get_user(ban.uid)
		if self.user is None:
			self.user = await self.bot.fetch_user(ban.uid)
