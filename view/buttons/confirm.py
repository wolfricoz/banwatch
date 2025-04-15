import discord.ui


class Confirm(discord.ui.View):

	"""This class is for the confirm buttons, which are used to confirm or cancel an action."""

	value = None


	async def send_confirm(self, interaction: discord.Interaction, message: str = "Do you want to proceed?"):
		"""send the confirm message"""
		await interaction.response.send_message(message, view=self, ephemeral=True)
		await self.wait()
		return self.value

	def __init__(self):
		super().__init__(timeout=None)

	@discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="confirm")
	async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
		"""confirm the action"""
		self.value = True
		await interaction.response.send_message("Confirmed", ephemeral=True)
		self.stop()

	@discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="cancel")
	async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
		"""cancel the action"""
		self.value = False
		await interaction.response.send_message("Cancelled", ephemeral=True)
		self.stop()
