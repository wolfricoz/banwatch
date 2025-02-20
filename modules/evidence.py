import logging
import os

import discord
from discord import app_commands
from discord.ext import commands

from classes.evidence import EvidenceController
from classes.queue import queue
from classes.support.discord_tools import await_message, send_response
from database.databaseController import BanDbTransactions, ProofDbTransactions
from view.pagination.pagination import Pagination


class Evidence(commands.GroupCog, name="evidence") :

	def __init__(self, bot: commands.Bot) :
		self.bot = bot

	@app_commands.command(name="add", description="Adds evidence to a user's record")
	@app_commands.checks.has_permissions(moderate_members=True)
	async def add(self, interaction: discord.Interaction, user: discord.User, ban_id: str = None) :
		"""Adds evidence to a user's record"""
		ban_entry: discord.Message
		if not ban_id :
			ban_id = interaction.guild.id + user.id
			try :
				await interaction.guild.fetch_ban(user)
			except discord.NotFound :
				await send_response(interaction, f"{user.mention} not found in this servers bans")
				return
		ban = BanDbTransactions().get(ban_id, override=True)
		if ban is None :
			queue().add(send_response(interaction,
			                          f"Ban ID {ban_id} not found, please check if the user is banned. If this error persists please open a ticket in the support server.", ephemeral=True),
			            priority=2)
			return
		queue().add(send_response(interaction, f"⏳ Processing Evidence, please wait.", ephemeral=True), priority=2)
		evidence_message = (
			f"Please send a message with the evidence you would like to add to {user.name}'s record, this will be added to the ban ID {ban_id} in our support server. \n Type `cancel` to cancel.\n-# By responding to this message you agree to the evidence being stored in our support server."
			f"\nPlease avoid uploading:"
			f"\n* Personal information (irl information such as a persons name, date of birth, where they live, government documentation, etc)"
			f"\n* We recommend you blur out any usernames or profile pictures of other users in the evidence for user safety."
			f"\n\n**Forwarded Messages are now officially supported.**")
		evidence = await await_message(interaction, evidence_message)
		if evidence is False :
			return
		queue().add(EvidenceController.add_evidence(interaction, evidence, ban_id, user), priority=2)

	@app_commands.command(name="get", description="Get the proof for an user's ban!")
	@app_commands.checks.has_permissions(moderate_members=True)
	async def get(self, interaction: discord.Interaction, user: discord.User = None, ban_id: str = None) :
		if user is None and ban_id is None :
			await send_response(interaction, "Please fill in the user or ban_id field to get the user.")

		if ban_id :
			entries = ProofDbTransactions().get(ban_id=ban_id)
			await EvidenceController().send_proof(interaction, entries, ban_id)
			return
		# user goes here
		entries = ProofDbTransactions().get(user_id=user.id)
		await EvidenceController().send_proof(interaction, entries, user.id)

	# Add a way to manage bans, both for staff of a server as well as the banwatch staff
	@app_commands.command(name="manage", description="View evidence and manage evidence")
	@app_commands.checks.has_permissions(moderate_members=True)
	async def manage(self, interaction: discord.Interaction, user: discord.User = None, ban_id: str = None) :
		if ban_id :
			entries = ProofDbTransactions().get(ban_id=ban_id)
			view = Pagination(entries)
			view.interaction = interaction
			return await view.send_view()
		# user goes here
		entries = ProofDbTransactions().get(user_id=user.id)
		view = Pagination(entries)
		view.interaction = interaction
		await view.send_view()


async def setup(bot: commands.Bot) :
	await bot.add_cog(Evidence(bot))
