import discord
from discord_py_utilities.messages import send_message, send_response


class CleanupButtons(discord.ui.View) :
	def __init__(self) :
		super().__init__(timeout=None)
		pass

	@discord.ui.button(label="Hide Message", style=discord.ButtonStyle.green, custom_id="clean_up")
	async def allow(self, interaction: discord.Interaction, button: discord.ui.Button) :
		"""This button removes the current message"""
		await interaction.message.delete()
		pass

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
