import json
import logging
import os

import discord

from database.transactions.ServerTransactions import ServerTransactions
from project.data import CACHE
from view.multiselect.CommandSelect import CommandSelect


class HelpLayout(discord.ui.LayoutView) :
	"""This is the 2.0 embed layout for onboarding messages."""
	content = (
		"## Banwatch Configuration Guide\n\n"
		"Welcome to Banwatch! This guide will walk you through setting up the bot on your server.\n\n"
		"### Setup\n"
		"Run `/config setup` for a guided setup, or set a moderator channel yourself. "
		"This is where the bot will post ban information.\n"
		"```\n"
		"/config change option:Mod channel channel:<#your-mod-channel>\n"
		"```\n\n"
		"### Permissions\n"
		"**Required server-wide:**\n"
		"*   **Ban Members**: to read your bans and use `/ban`.\n"
		"*   **View Audit Log**: to read ban reasons.\n\n"
		"**Required in the mod channel:** **View Channel**, **Send Messages** and **Embed Links**.\n\n"
		"**Optional:** **Attach Files** and **Read Message History** in the mod channel (evidence, updating ban "
		"messages); **Kick Members**, **Manage Messages**, **Manage Server** and **Create Invite** server-wide "
		"for warnings, clean-up and the dashboard. Automatic setup also needs **Manage Channels** to create "
		"the alerts channel.\n\n"
		"### Debugging\n"
		"`/config permissioncheck` shows exactly which of these are missing and how to fix them.\n\n"
		"### Commands\n"
		"Pick any command from the menu below to read what it does.\n"
	)

	commands = []

	def __init__(self, content=None) :
		super().__init__(timeout=None)
		self.commands = []
		self.command_docs = {}
		if content :
			self.content = content
		self.reason = None
		self.interaction = None
		self.current_page = 0

		# Define components
		self.container = discord.ui.Container(
			discord.ui.TextDisplay(content=self.content),
			discord.ui.Separator(visible=True),
			accent_colour=discord.Colour.purple()
		)

		self.links = discord.ui.ActionRow()
		self.links.add_item(
			discord.ui.Button(label="Dashboard Setup", style=discord.ButtonStyle.link, url=os.getenv("DASHBOARD_URL")))
		self.links.add_item(discord.ui.Button(label="Documentation", style=discord.ButtonStyle.link,
		                                      url="https://wolfricoz.github.io/banwatch/"))
		support_server = ServerTransactions().get(int(os.getenv("GUILD")))
		if support_server is not None :
			self.links.add_item(
				discord.ui.Button(label="Support Server", style=discord.ButtonStyle.link, url=support_server.invite))

		self.selectrow = discord.ui.ActionRow()
		self.buttonrow = discord.ui.ActionRow()

		# Add components to the view
		self.add_item(self.container)
		self.add_item(self.links)
		self.add_item(self.selectrow)
		self.add_item(self.buttonrow)

		self.reasons = []
		try :
			with open(CACHE, "r", encoding="utf-8") as cachefile :
				self.command_docs = json.load(cachefile)
		except (FileNotFoundError, json.JSONDecodeError) :
			self.command_docs = {"No Commands Found" : "The command documentation cache is missing or corrupted."}

		for command, description in self.command_docs.items() :
			self.reasons.append(discord.SelectOption(label=command, description=description[:100]))

		self.items_per_page = 25
		self.total_pages = (len(self.reasons) + self.items_per_page - 1) // self.items_per_page

		self._update_page()

	# ============================================================
	def _update_page(self) :
		logging.info(f"Updating page: {self.current_page}")
		# Clear the rows
		self.selectrow.clear_items()
		self.buttonrow.clear_items()

		# Calculate slice for current page
		start = self.current_page * self.items_per_page
		end = start + self.items_per_page
		page_reasons = self.reasons[start :end]

		# Add select menu to its own row
		# The pager only changes which commands the menu lists, so say that rather than "Page 1/2",
		# which reads as if the guide text above should change too.
		shown = f"commands {start + 1}–{min(end, len(self.reasons))} of {len(self.reasons)}"
		placeholder = f"Pick a command ({shown})" if self.total_pages > 1 else "Pick a command to read about it"
		select = CommandSelect(page_reasons, self, placeholder=placeholder)
		self.selectrow.add_item(select)

		# logging.info(f"Total pages: {self.total_pages}, Current page: {self.current_page}")

		if self.total_pages > 1 :
			# Previous button
			prev_button = discord.ui.Button(
				label="◀ Previous commands",
				style=discord.ButtonStyle.primary,
				disabled=(self.current_page == 0)
			)
			prev_button.callback = self._previous_page
			self.buttonrow.add_item(prev_button)

			# Page indicator
			page_button = discord.ui.Button(
				label=shown.capitalize(),
				style=discord.ButtonStyle.secondary,
				disabled=True
			)
			self.buttonrow.add_item(page_button)

			# Next button
			next_button = discord.ui.Button(
				label="More commands ▶",
				style=discord.ButtonStyle.primary,
				disabled=(self.current_page >= self.total_pages - 1)
			)
			next_button.callback = self._next_page
			self.buttonrow.add_item(next_button)

	# ============================================================
	async def _previous_page(self, interaction: discord.Interaction) :
		self.current_page = max(0, self.current_page - 1)
		self._update_page()
		await interaction.response.edit_message(view=self)

	# ============================================================
	async def _next_page(self, interaction: discord.Interaction) :
		self.current_page = min(self.total_pages - 1, self.current_page + 1)
		self._update_page()
		await interaction.response.edit_message(view=self)
