import os

import discord
from discord.ui import View
from discord_py_utilities.messages import send_message, send_response

from classes.configdata import ConfigData
from database.databaseController import AppealMsgTransactions, AppealsDbTransactions, BanDbTransactions
from view.modals.inputmodal import send_modal
from view.multiselect.statusselect import SelectStatus


class AppealButtons(View) :
	bot = None

	def __init__(self, response=False) :
		super().__init__(timeout=None)
		self.response = response
		if response :
			self.change_status.disabled = True

	@discord.ui.button(label="Change Status", style=discord.ButtonStyle.success, custom_id="ChangeStatus")
	async def change_status(self, interaction: discord.Interaction, button: discord.ui.Button) :
		await self.load_data(interaction)
		await send_response(interaction, "Choose the status of the appeal", view=SelectStatus(self.ban_id))

	# await self.disable_buttons(interaction)

	@discord.ui.button(label="Respond", style=discord.ButtonStyle.success, custom_id="Respond")
	async def respond(self, interaction: discord.Interaction, button: discord.ui.Button) :
		await self.load_data(interaction)
		appeal = AppealsDbTransactions().get(self.ban_id)
		if not appeal :
			await send_response(interaction, f"This appeal no longer exists. Please create a new appeal")
			await self.disable_buttons(interaction)
			return
		target = "guild" if self.dmChannel else "user"
		message = await send_modal(interaction, f"Your response has been delivered to the {target}", "What's your message?", 2000)

		await self.send_embed(interaction, message)
		await self.create_record(interaction, message, appeal)
		if self.response :
			await self.disable_buttons(interaction)

	@discord.ui.button(label="Report", style=discord.ButtonStyle.danger, custom_id="Report")
	async def report(self, interaction: discord.Interaction, button: discord.ui.Button) :
		await self.load_data(interaction)
		staff_channel = self.bot.get_channel(int(os.getenv("BANS")))
		await send_message(staff_channel, f"Report abuse from {interaction.guild.name} for appeal: {self.ban_id}",
		                   embed=interaction.message.embeds[0])
		await send_response(interaction, f"Successfully sent the report to the banwatch staff!")
		AppealsDbTransactions().change_status(self.ban_id, "denied")
		await self.disable_buttons(interaction)

	async def disable_buttons(self, interaction: discord.Interaction) :
		for child in self.children :
			child.disabled = True
		await interaction.message.edit(view=self)

	async def send_embed(self, interaction: discord.Interaction, content) :
		title = await self.create_title(interaction)
		embed = discord.Embed(title=title, color=discord.Color.green(), description=content)
		embed.set_footer(text=self.ban_id)
		try :
			if self.dmChannel :
				channel = self.guild.get_channel(ConfigData().get_key_or_none(self.ban.gid, 'modchannel'))
				await send_message(channel, " ", embed=embed, view=AppealButtons(response=True))
				return
			await send_message(self.user, " ", embed=embed, view=AppealButtons(response=True))
		except discord.Forbidden :
			await send_message(interaction.channel, f"Unable to send message to {self.user.name}, DMs are closed.")

	async def create_title(self, interaction: discord.Interaction) :
		if self.dmChannel:
			return f"Response from {interaction.user.name} for ban id: {self.ban_id}"
		return f"Response from {interaction.guild.name} for ban id: {self.ban_id}"

	async def create_record(self, interaction, message, appeal):
		if self.dmChannel:
			return AppealMsgTransactions.add(message, self.user.id, self.ban.gid, appeal.id)
		return AppealMsgTransactions.add(message, self.ban.gid, self.user.id,  appeal.id)


	async def load_data(self, interaction: discord.Interaction) :
		self.bot = interaction.client
		self.dmChannel = isinstance(interaction.channel, discord.DMChannel)
		self.ban_id = interaction.message.embeds[0].footer.text
		ban = BanDbTransactions().get(self.ban_id, override=True)
		self.ban = ban
		self.guild = self.bot.get_guild(ban.gid)
		self.user = self.bot.get_user(ban.uid)
		if self.user is None :
			self.user = await self.bot.fetch_user(ban.uid)
