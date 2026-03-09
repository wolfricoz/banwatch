import asyncio
import logging
import os

import discord
from discord_py_utilities.bans import ban_user
from discord_py_utilities.messages import await_message, send_message, send_response

from classes.bans import Bans as BansClass
from classes.evidence import EvidenceController
from classes.queue import queue
from data.variables.messages import evidence_message_template
from database.current import Bans
from database.transactions.BanTransactions import BanTransactions
from database.transactions.ServerTransactions import ServerTransactions
from view.buttons.lookup import LookUp
from view.modals.inputmodal import send_modal
from view.multiselect.selectreason import SelectReason


class BanInfo(discord.ui.LayoutView) :
	"""This is the 2.0 embed layout for onboarding messages."""

	def __init__(self, user: discord.User, ban: Bans) :
		super().__init__(timeout=None, )
		self.reason: str = "This user is not banned in this server."
		self.title = f"Manage {user.global_name} ({user.id})'s ban!"
		self.user = user
		self.ban_entry = ban
		if ban :
			self.reason = ban.reason

		container = discord.ui.Container(
			discord.ui.TextDisplay(
				content=f"**{self.title}**"  # Bold markdown for hierarchy
			),

			discord.ui.Separator(visible=True),

			# This is your main body area
			discord.ui.TextDisplay(
				content=self.reason  # Keeps the space open but clean
			),
			discord.ui.Separator(visible=True),

			# If you want a footer style, add another TextDisplay here
			discord.ui.TextDisplay(
				content="-# _You can select an action below to manage this user._"  # Italics for a 'hint' feel
			),

			accent_colour=discord.Colour.purple()
		)
		self.add_item(container)

		actions = discord.ui.ActionRow()
		if ban :
			# === Options ===
			reban = discord.ui.Button(
				custom_id="ban_management_reban",
				label="Update ban reason",
				style=discord.ButtonStyle.primary,
				emoji="📝"
			)
			evidence = discord.ui.Button(
				custom_id="ban_management_evidence",
				label="Add Evidence",
				style=discord.ButtonStyle.primary,
				emoji="📁"
			)
			unban = discord.ui.Button(
				custom_id="ban_management_unban",
				label="Unban User",
				style=discord.ButtonStyle.danger,
				emoji="🔓"
			)
			hide = discord.ui.Button(
				custom_id="ban_management_hide",
				label="Hide Ban",
				style=discord.ButtonStyle.danger,
				emoji="❌"
			)
			# === add callbacks ===
			reban.callback = self.reban
			evidence.callback = self.evidence
			unban.callback = self.unban
			hide.callback = self.hide
			actions.add_item(reban)
			actions.add_item(evidence)
			actions.add_item(unban)
			actions.add_item(hide)

		else :
			ban_button = discord.ui.Button(
				custom_id="ban_management_ban",
				label="Ban User",
				style=discord.ButtonStyle.danger,
				emoji="🔨"
			)
			ban_button.callback = self.ban_button
			actions.add_item(ban_button)

		history = discord.ui.Button(
			custom_id="ban_management_history",
			label="View Ban Record",
			style=discord.ButtonStyle.danger,
			emoji="🗒️"
		)
		history.callback = self.history
		actions.add_item(history)

		self.add_item(actions)
		self.add_support_guild_button()

	custom_id = "BanManagementModal"

	# === For users with bans ===

	async def reban(self, interaction: discord.Interaction) :
		if not self.check_perms(interaction) :
			return await send_response(interaction, f"You don't have permission for this action", ephemeral=True)
		await self._ban(interaction)

	async def evidence(self, interaction: discord.Interaction) :
		if not self.check_perms(interaction) :
			return await send_response(interaction, f"You don't have permission for this action", ephemeral=True)
		evidence = await await_message(interaction, evidence_message_template.format(user=self.user.name,
		                                                                             ban_id=self.user.id + interaction.guild.id))
		if evidence is False :
			return None
		await send_response(interaction, f"⏳ Processing Evidence, please wait.", ephemeral=True)
		queue().add(EvidenceController.add_evidence(interaction, evidence, self.user.id + interaction.guild.id, self.user),
		            priority=2)
		return None

	async def unban(self, interaction: discord.Interaction) :
		if not self.check_perms(interaction) :
			return await send_response(interaction, f"You don't have permission for this action", ephemeral=True)
		await interaction.guild.unban(self.user, reason=f"Unbanned by {interaction.user.name}")
		await send_response(interaction, f"{self.user.mention} unbanned by {interaction.user.mention}")

	async def hide(self, interaction: discord.Interaction) :
		if not self.check_perms(interaction) :
			return await send_response(interaction, f"You don't have permission for this action", ephemeral=True)
		BanTransactions().update(self.ban_entry, hidden=True)
		await BansClass().revoke_bans(interaction.client, self.user.id + interaction.guild.id,
		                              "Ban has been hidden by the server.")
		await send_response(interaction, f"{self.user.mention}'s ban has been hidden by {interaction.user.name}")

	# === For users without bans ===
	async def ban_button(self, interaction: discord.Interaction) :
		if not self.check_perms(interaction) :
			return await send_response(interaction, f"You don't have permission for this action", ephemeral=True)
		await self._ban(interaction)

	async def history(self, interaction: discord.Interaction) :
		if not self.check_perms(interaction) :
			return await send_response(interaction, f"You don't have permission for this action", ephemeral=True)
		# Fetch all bans for the specified user
		user = self.user
		override = False
		sr = BanTransactions().get_all_user(user_id=user.id, override=override)
		if sr is None :  # If no bans are found, notify the user
			logging.info(f"No bans found for user {user.id}.")
			await send_response(interaction, f"<@{user.id}> is not banned in any servers the bot is in.")
			return

		# Notify the user that bans are being fetched
		await send_response(interaction, "⌛ Fetching bans, please wait.", ephemeral=True)

		# Create a view for displaying the bans and send the details
		view: LookUp = LookUp(user_id=user.id)
		logging.info(f"Sending ban details for user {user.id}.")
		await view.send_message(interaction.client, interaction.channel, sr, user, interaction=interaction,
		                        override=override)
		return None

	# === support functions ===
	async def _ban(self, interaction: discord.Interaction) :
		view = SelectReason()
		await send_message(interaction.channel, "Select your reason.", view=view)
		await view.wait()
		reason = view.get_reason()
		if reason == "custom" :
			reason = await send_modal(interaction, "What is the reason for the ban?", "Ban Reason")
		try :
			await interaction.guild.unban(self.user, reason=reason)
		except discord.errors.NotFound :
			pass
		await asyncio.sleep(3)
		try :
			await ban_user(interaction, self.user, "", reason, inform=False, ban_class=BansClass())
		except discord.Forbidden :
			await send_response(interaction, "I don't have permission to ban this user")

	def check_perms(self, interaction: discord.Interaction) :
		if interaction.user.guild_permissions.ban_members :
			return True
		return False

	def add_support_guild_button(self) :
		support_server = ServerTransactions().get(int(os.getenv("GUILD")))
		links = discord.ui.ActionRow()
		if support_server is not None :
			links.add_item(
				discord.ui.Button(label="Support Server", style=discord.ButtonStyle.link, url=support_server.invite))
		self.add_item(links)
