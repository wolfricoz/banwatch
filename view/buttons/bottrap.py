import logging

import discord
from discord_py_utilities.messages import send_message, send_response

from classes.access import AccessControl
from classes.configdata import ConfigData


class bottrap(discord.ui.View) :
	def __init__(self) :
		super().__init__(timeout=None)
		pass

	@discord.ui.button(label="I", style=discord.ButtonStyle.green, custom_id="bottrap_i")
	async def i_button(self, interaction: discord.Interaction, button: discord.ui.Button) :
		"""First word button"""
		await self.trigger(interaction)

	@discord.ui.button(label="am", style=discord.ButtonStyle.green, custom_id="bottrap_am")
	async def am_button(self, interaction: discord.Interaction, button: discord.ui.Button) :
		"""Second word button"""
		await self.trigger(interaction)

	@discord.ui.button(label="a", style=discord.ButtonStyle.green, custom_id="bottrap_a")
	async def a_button(self, interaction: discord.Interaction, button: discord.ui.Button) :
		"""Third word button"""
		await self.trigger(interaction)

	@discord.ui.button(label="bot", style=discord.ButtonStyle.green, custom_id="bottrap_bot")
	async def bot_button(self, interaction: discord.Interaction, button: discord.ui.Button) :
		"""Fourth word button"""
		await self.trigger(interaction)

	async def disable_buttons(self, interaction: discord.Interaction) :
		for item in self.children :
			item.disabled = True
		try :
			await interaction.message.edit(view=self)
		except Exception :
			pass

	async def load_data(self, interaction: discord.Interaction) :
		"""Load data from embed"""
		if len(interaction.message.embeds) < 1 :
			return False
		return True

	async def trigger(self, interaction: discord.Interaction) :
		"""The bottrap has been triggered, and bans the user"""
		if not AccessControl().is_premium(interaction.guild.id):
			await send_response(interaction, "This server does not have premium access, bottrap is disabled.", ephemeral=True)
			await interaction.message.delete()
			return
		logging.info(ConfigData().get_key(interaction.guild.id, "modchannel"))
		modchannel = interaction.guild.get_channel(ConfigData().get_key(interaction.guild.id, "modchannel"))
		if modchannel is None:
			modchannel = await interaction.guild.fetch_channel(ConfigData().get_key(interaction.guild.id, "modchannel"))
		if modchannel is None:
			return
		await send_message(modchannel, f"Bottrap triggered by {interaction.user.name} ({interaction.user.id})")
		await interaction.guild.ban(interaction.user, reason="Member pressed the bot trap buttons.")