from typing import List
import discord
from discord_py_utilities.bans import ban_user
from discord_py_utilities.messages import await_message, send_message, send_response

from classes.bans import Bans
from classes.warnings.evidence import WarningEvidence
from data.variables.messages import evidence_message_template, evidence_warning_message_template
from database.current import Warnings
from database.transactions.WarningTransactions import WarningTransactions
from view.buttons.confirm import Confirm


class WarningManager(discord.ui.LayoutView) :
	"""This is the 2.0 embed layout for managing user warnings with pagination."""

	def __init__(self, user: discord.User, warnings: List["Warnings"]) :
		super().__init__(timeout=None)

		self.user = user
		self.warnings = warnings
		self.current_page = 0
		self.total_pages = len(warnings)

		# 1. Create the TextDisplay container for our warning data
		self.text_display = discord.ui.Container(
			discord.ui.TextDisplay(content=self.get_display_content())
		)

		# 2. Create the ActionRow containers manually
		self.row_0 = discord.ui.ActionRow()  # For pagination controls
		self.row_1 = discord.ui.ActionRow()  # For moderation action items

		# 3. Define the button instances
		self.prev_page = discord.ui.Button(
			label="◀",
			style=discord.ButtonStyle.secondary,
			custom_id="warn_prev"
		)
		self.prev_page.callback = self.prev_page_callback

		self.next_page = discord.ui.Button(
			label="▶",
			style=discord.ButtonStyle.secondary,
			custom_id="warn_next"
		)
		self.next_page.callback = self.next_page_callback

		self.add_evidence_btn = discord.ui.Button(
			label="Add Evidence",
			style=discord.ButtonStyle.primary,
			custom_id="warn_add_evidence"
		)
		self.add_evidence_btn.callback = self.add_evidence_callback

		self.delete_btn = discord.ui.Button(
			label="Delete",
			style=discord.ButtonStyle.danger,
			custom_id="warn_delete"
		)
		self.delete_btn.callback = self.delete_warning_callback

		self.ban_btn = discord.ui.Button(
			label="Ban User",
			style=discord.ButtonStyle.danger,
			custom_id="warn_ban"
		)
		self.ban_btn.callback = self.ban_user_callback

		# 4. Pack buttons into their respective ActionRows
		self.row_0.add_item(self.prev_page)
		self.row_0.add_item(self.next_page)

		self.row_1.add_item(self.add_evidence_btn)
		self.row_1.add_item(self.delete_btn)
		self.row_1.add_item(self.ban_btn)

		# 5. Add components directly to the LayoutView (Text first, then buttons)
		self.add_item(self.text_display)
		self.add_item(self.row_0)
		self.add_item(self.row_1)

		# Update button states right at initialization
		self.update_button_states()

	def get_display_content(self) -> str :
		"""Generates the Markdown string content for the TextDisplay layer."""
		if not self.warnings :
			return f"### Manage {self.user.global_name}'s Warnings\nThis user has no warnings."

		current_warning = self.warnings[self.current_page]

		# Using markdown formatting for a clean v2 display interface
		content = (
			f"### Managing {self.user.global_name} ({self.user.id})'s Warnings\n"
			f"**Warning ID:** {current_warning.id}\n"
			f"**Guild ID:** {current_warning.guild_id}\n"
			f"**Reason:** {current_warning.reason}\n\n"
			f"*Warning {self.current_page + 1} of {self.total_pages}*"
		)
		return content

	def create_embed(self) -> discord.Embed :
		"""Generates the background card embed for layout context."""
		embed = discord.Embed(color=discord.Color.orange())
		return embed

	def update_button_states(self) :
		"""Helper to enable/disable navigation buttons based on the current page."""
		if self.total_pages <= 1 :
			self.prev_page.disabled = True
			self.next_page.disabled = True
			return

		self.prev_page.disabled = self.current_page == 0
		self.next_page.disabled = self.current_page == self.total_pages - 1

	async def update_view(self, interaction: discord.Interaction) :
		"""Updates the text container and components after page change."""
		self.update_button_states()



		# Crucial for v2 components: update the content of the TextDisplay before editing
		self.text_display.children[0].content = self.get_display_content()



		await interaction.response.edit_message(view=self)

	# --- CALLBACKS ---

	async def prev_page_callback(self, interaction: discord.Interaction) :
		if self.current_page > 0 :
			self.current_page -= 1
			await self.update_view(interaction)
		else :
			await interaction.response.defer()

	async def next_page_callback(self, interaction: discord.Interaction) :
		if self.current_page < self.total_pages - 1 :
			self.current_page += 1
			await self.update_view(interaction)
		else :
			await interaction.response.defer()

	async def add_evidence_callback(self, interaction: discord.Interaction) :
		current_warning = self.warnings[self.current_page] if self.warnings else None
		evidence = await await_message(interaction, evidence_warning_message_template.format(user=self.user.name, warning_id=current_warning.id))
		if evidence is False :
			return
		manager = WarningEvidence(current_warning)
		await manager.create_evidence(evidence)

	async def delete_warning_callback(self, interaction: discord.Interaction) :
		current_warning = self.warnings[self.current_page] if self.warnings else None
		WarningTransactions().delete_warning(current_warning.id)
		self.warnings.pop(self.current_page)
		self.current_page -= 1
		self.total_pages = len(self.warnings)
		await self.update_view(interaction)
		await send_message(interaction.channel,
			f"{interaction.user.mention} deleted warning `{current_warning.reason}` from {self.user.global_name}.",
		)

	async def ban_user_callback(self, interaction: discord.Interaction) :

		current_warning = self.warnings[self.current_page]
		confirm = Confirm()
		# Confirm that you want to ban
		await confirm.send_confirm(interaction, f"Do you want to ban {self.user.name} with reason:\n`{current_warning.reason}`")
		if not confirm.value:
			return

		# Ban the user
		await ban_user(interaction, self.user, "", current_warning.reason, ban_class=Bans())
