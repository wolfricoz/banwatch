import logging
from typing import Any

import discord
from discord import Interaction
from discord.ext import commands
from discord.ui import Item
from discord_py_utilities.messages import send_message
from discord_py_utilities.permissions import check_missing_channel_permissions

from classes.evidence import EvidenceController
from database.databaseController import ProofDbTransactions
from view.base.secureview import SecureView
from view.multiselect.selectban import SelectBan


class LookUp(SecureView) :
	bot = None

	def __init__(self, user_id=None) :
		super().__init__(timeout=None)
		if not user_id :
			return
		entries = ProofDbTransactions().get(user_id=user_id)
		if not entries :
			self.evidence.disabled = True

	async def send_message(self, bot: commands.Bot, channel: discord.TextChannel, sr,
	                       user: discord.Member | discord.User, excess=True, interaction: discord.Interaction = None, override=False) :
		logging.info(f"Starting send_message for user {user.name}({user.id}) in channel {channel.name}({channel.id})")

		# Check permissions
		logging.info(f"Checking permissions for channel {channel.name}({channel.id})")
		permissions = ['view_channel', 'send_messages', 'embed_links', 'attach_files']
		if missing := check_missing_channel_permissions(channel, permissions) :
			logging.error(f"Missing permission to send message to {channel.name}")
			if interaction:
				return await send_message(interaction.user, f"Missing permission to send ban information for {user.name} to {channel.name}. Check permissions: {', '.join(missing)}")

			return await send_message(channel.guild.owner,
				f"Missing permission to send ban information for {user.name} to {channel.name}. Check permissions: {', '.join(missing)}")
		logging.info("All required permissions are present")

		# Handle empty ban list
		if len(sr) <= 0 or not sr :
			logging.info(f"No bans found for user {user.name}({user.id})")
			nfembed = discord.Embed(title=f"{user.name}({user.id})'s ban history.", description="No bans found.")
			await send_message(channel, embed=nfembed)
			return

		# Initialize variables for processing bans
		logging.info(f"Processing {len(sr)} bans for user {user.name}({user.id})")
		characters = 0
		count = 0
		bans = []
		embed = discord.Embed(
			title=f"{user.name}({user.id})'s ban history",
			description="Please ensure to reach out to the respective servers for proof or check the support server before taking any action.\n\nIf you ban based upon a ban, please include 'Cross-ban from (server-name):' in front of it."
		)
		embed.set_footer(text=f"{user.id}")

		# Process each ban
		for i, ban in enumerate(sr) :
			logging.debug(f"Processing ban {i + 1}/{len(sr)}: {ban}")
			if count >= 10 :
				logging.info(f"Sending batch of 10 bans to channel {channel.name}({channel.id})")
				await send_message(channel, embed=embed, view=self)
				embed.clear_fields()
				count = 0
			count += 1
			guild = bot.get_guild(ban.gid)
			staff_data = f"approved: {ban.approved}, hidden: {ban.hidden}"
			created_at = ban.created_at.strftime(
				'%m/%d/%Y') if ban.message else 'pre-banwatch, please check with server owner.'
			embed.add_field(
				name=f"{guild.name} ({ban.guild.invite}) (ban_id: {ban.ban_id})",
				value=f"{ban.reason}\n"
				      f"verified: {'Yes' if ban.verified else 'No'}, date: {created_at}{f', {staff_data}' if override else ''}",
				inline=False
			)

		# Finalize and send remaining bans
		sr = "\n".join(bans)
		if len(sr) == 0 :
			logging.info(f"Sending final embed for user {user.name}({user.id})")
			await send_message(channel, embed=embed, view=self)
			return

		await send_message(channel, embed=embed, view=self)
		while characters < len(sr) :
			logging.info(f"Sending remaining characters {characters} to {characters + 1800} for user {user.name}({user.id})")
			await send_message(channel, sr[characters :characters + 1800])
			characters += 1800

		logging.info(f"Completed send_message for user {user.name}({user.id})")
	async def get_user_id(self, interaction: discord.Interaction) :
		embed = interaction.message.embeds[0]
		return int(embed.footer.text)

	@discord.ui.button(label="view evidence", style=discord.ButtonStyle.primary, custom_id="banoptions_evidence")
	async def evidence(self, interaction: discord.Interaction, button: discord.ui.Button) :
		user_id = await self.get_user_id(interaction)
		entries = ProofDbTransactions().get(user_id=user_id)
		await EvidenceController().send_proof(interaction, entries, user_id)

	@discord.ui.button(label="Cross-ban", style=discord.ButtonStyle.danger, custom_id="Cross-ban")
	async def cross_ban(self, interaction: discord.Interaction, button: discord.ui.Button) :
		user_id = await self.get_user_id(interaction)
		await interaction.response.send_message("Please select which server you want to cross-ban from.", view=SelectBan(user_id), ephemeral=True)

	async def on_error(self, interaction: Interaction, error: Exception, item: Item[Any], /) -> None:
		"""This function is called when an error occurs in the view."""
		logging.info(f"Error in {interaction.message.id}: {error}")
		await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)
		await super().on_error(interaction, error, item)