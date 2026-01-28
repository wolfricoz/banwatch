import discord
from discord import app_commands
from discord.ext import commands
from discord_py_utilities.messages import send_response

from view.v2.HelpLayout import HelpLayout


class Utility(commands.Cog, description="Miscellaneous utility commands for general use.") :

	def __init__(self, bot: commands.Bot) :
		self.bot = bot

	@app_commands.command(name="help", description="Unsure of what a command does? Find it here!")
	async def help(self, interaction: discord.Interaction) :
		"""Provides information about the bot's commands and features."""

		help_text = (
			"**Bot Help Guide**\n\n"
			"To view the documentation of a command, please select it from the select menu below.\n\n"
		)
		helplayout = HelpLayout(help_text)

		await send_response(interaction, " ", view=helplayout, ephemeral=True)

	@app_commands.command(name="support", description="Get a link to the support server and documentation.")
	async def support(self, interaction: discord.Interaction) :
		"""
		Provides a link to the official documentation and support server. Use this if you need help with the bot or want to report an issue.

		**Permissions:**
		- None required for the user.
		"""
		await interaction.response.send_message(
			"If you are in need of support, please read our documentation at https://wolfricoz.github.io/banwatch/ ! You can find our discord link in the documentation. If you still need help, please join our discord server and ask in the support channel.",
			ephemeral=True)

	@app_commands.command(name="donate", description="If you like banwatch, consider donating!")
	async def donate(self, interaction: discord.Interaction) :
		"""
		Provides a link to financially support the development and hosting of BanWatch. Donations help keep the bot running and support future updates.

		**Permissions:**
		- None required for the user.
		"""
		await send_response(interaction,
		                    f"If you like the service banwatch provides and would like to financially support banwatch, you can do so here: https://buy.stripe.com/7sYbJ17fYeGY45bgygao803")


async def setup(bot: commands.Bot) :
	await bot.add_cog(Utility(bot))
