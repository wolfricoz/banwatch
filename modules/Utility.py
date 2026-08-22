import logging
import os
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands
from discord_py_utilities.messages import send_message, send_response

from project.data import CONTACT_EMAIL, DOCUMENTATION
from view.modals.inputmodal import send_modal
from view.v2.HelpLayout import HelpLayout


class Utility(commands.Cog, description="Miscellaneous utility commands for general use.") :

	def __init__(self, bot: commands.Bot) :
		self.bot = bot

	# ============================================================
	@app_commands.command(name="help", description="Unsure of what a command does? Find it here!")
	async def help(self, interaction: discord.Interaction) :
		"""Provides information about the bot's commands and features."""

		help_text = (
			"**Bot Help Guide**\n\n"
			"To view the documentation of a command, please select it from the select menu below.\n\n"
		)
		helplayout = HelpLayout(help_text)

		await send_response(interaction, " ", view=helplayout, ephemeral=True)

	# ============================================================
	@app_commands.command(name="support", description="Get a link to the support server and documentation.")
	async def support(self, interaction: discord.Interaction) :
		"""
		Provides a link to the official documentation and support server. Use this if you need help with the bot or want to report an issue.

		**Permissions:**
		- None required for the user.
		"""
		await interaction.response.send_message(
			f"If you are in need of support, please read our documentation at {DOCUMENTATION} ! You can find our discord link in the documentation. If you still need help, please join our discord server and ask in the support channel."
			f"\n\nDon't want to (or can't) use discord? Use `/report_issue` to send a report straight to the developers, or email us at {CONTACT_EMAIL}. Data protection requests can be sent to that address as well.",
			ephemeral=True)

	# ============================================================
	@app_commands.command(name="report_issue", description="Report a problem with Banwatch itself to the developers.")
	async def report_issue(self, interaction: discord.Interaction) :
		"""
		Reports a problem with the bot itself, such as a bug, misuse of the bot, or a request about your personal data.
		The report is delivered to the developers and the contact email is included in the confirmation, so there is
		always a route to us that does not depend on discord.

		**Permissions:**
		- None required for the user.
		"""
		issue = await send_modal(interaction,
		                         f"Thank you, your report has been sent to the developers. You can also reach us at {CONTACT_EMAIL} if you would rather not use discord, or if you don't hear back from us.",
		                         "What issue would you like to report?", 2000)
		if not issue :
			return
		embed = discord.Embed(title=f"Issue reported by {interaction.user}", description=issue,
		                      color=discord.Color.orange(), timestamp=datetime.now())
		embed.add_field(name="Reported by", value=f"{interaction.user}({interaction.user.id})")
		embed.add_field(name="Server",
		                value=f"{interaction.guild.name}({interaction.guild.id})" if interaction.guild else "Direct message")
		embed.set_footer(text=f"Reply by email: {CONTACT_EMAIL}")
		channel = self.bot.get_channel(int(os.getenv("DEV")))
		if channel is None :
			logging.error(f"Issue report by {interaction.user.id} could not be delivered: dev channel not found")
			return await interaction.followup.send(
				f"We could not deliver your report automatically, please email it to {CONTACT_EMAIL} instead.",
				ephemeral=True)
		await send_message(channel, " ", embed=embed)

	# ============================================================
	@app_commands.command(name="donate", description="If you like banwatch, consider donating!")
	async def donate(self, interaction: discord.Interaction) :
		"""
		Provides a link to financially support the development and hosting of BanWatch. Donations help keep the bot running and support future updates.

		**Permissions:**
		- None required for the user.
		"""
		await send_response(interaction,
		                    f"If you like the service banwatch provides and would like to financially support banwatch, you can do so here: https://buy.stripe.com/7sYbJ17fYeGY45bgygao803")

	# ============================================================
	@app_commands.command(name="clean_messages", description="Clean messages from banwatch in a channel.")
	@app_commands.checks.has_permissions(manage_messages=True)
	async def clean_messages(self, interaction: discord.Interaction, channel: discord.TextChannel,  limit: int = 100):
		"""
		Cleans up messages sent by BanWatch in the current channel. This is useful for removing old ban notifications or clutter.

		**Permissions:**
		- Requires `Manage Messages` permission.
		"""
		deleted = await channel.purge(limit=limit, check=lambda m: m.author == self.bot.user)
		await send_response(interaction, f"Deleted {len(deleted)} messages sent by BanWatch.", ephemeral=True)


async def setup(bot: commands.Bot) :
	await bot.add_cog(Utility(bot))
