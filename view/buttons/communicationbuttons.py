import logging
import os

import discord
from discord.ui import View
from discord_py_utilities.messages import send_message, send_response

from classes.configdata import ConfigData
from database.databaseController import AppealMsgTransactions, AppealsDbTransactions, BanDbTransactions
from view.modals.inputmodal import send_modal
from view.multiselect.statusselect import SelectStatus


class CommunicationButtons(View) :
	bot = None

	def __init__(self) :
		super().__init__(timeout=None)


	@discord.ui.button(label="Respond", style=discord.ButtonStyle.success, custom_id="Respond")
	async def respond(self, interaction: discord.Interaction, button: discord.ui.Button) :
		await self.load_data(interaction)
		message = await send_modal(interaction, f"Your response has been delivered to {self.recipient.name}", "What's your message?", 2000)
		await self.send_embed(interaction, message)
		await self.disable_buttons(interaction)

	@discord.ui.button(label="Report", style=discord.ButtonStyle.danger, custom_id="Report")
	async def report(self, interaction: discord.Interaction, button: discord.ui.Button) :
		await self.load_data(interaction)
		staff_channel = self.bot.get_channel(int(os.getenv("BANS")))
		await send_message(staff_channel, f"Report abuse from {interaction.guild.name} for appeal: {self.ban_id}",
		                   embed=interaction.message.embeds[0])
		await send_response(interaction, f"Successfully sent the report to the banwatch staff!")

	async def disable_buttons(self, interaction: discord.Interaction) :
		for child in self.children :
			child.disabled = True
		await interaction.message.edit(view=self)

	async def send_embed(self, interaction: discord.Interaction, content) :
		title = await self.create_title(interaction)
		embed = discord.Embed(title=title, color=discord.Color.green(), description=content)
		embed.set_footer(text=f"{interaction.guild.id}-{self.ban_id}")
		try :

			channel = self.recipient.get_channel(ConfigData().get_key_or_none(self.recipient.id, 'modchannel'))
			if channel is None:
				channel = await self.recipient.fetch_channel(ConfigData().get_key_or_none(self.recipient.id, 'modchannel'))

			if channel is None:
				return await send_message(interaction.channel, f"Could not deliver message because guild is not configured")

			await send_message(channel, " ", embed=embed, view=CommunicationButtons())
		except discord.Forbidden :
			await send_message(interaction.channel, f"Unable to send message to {self.recipient.name}, DMs are closed.")
		await self.disable_buttons(interaction)

	async def create_title(self, interaction: discord.Interaction) :
		return f"Response from {interaction.guild.name} for ban id: {self.ban_id}"



	async def load_data(self, interaction: discord.Interaction) :
		self.bot = interaction.client
		footer_list = interaction.message.embeds[0].footer.text.split('-')
		self.recipient = self.bot.get_guild(footer_list[0])
		logging.info(footer_list)
		if self.recipient is None :
			self.recipient = await self.bot.fetch_guild(footer_list[0])
		self.ban_id = footer_list[1]
		ban = BanDbTransactions().get(self.ban_id, override=True)
		self.ban = ban
		self.guild = self.bot.get_guild(ban.gid)
		self.user = self.bot.get_user(ban.uid)
		if self.user is None :
			self.user = await self.bot.fetch_user(ban.uid)
