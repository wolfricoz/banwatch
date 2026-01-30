import os
from typing import Any

import discord
from discord import Interaction
from discord.ui import Item, button
from discord_py_utilities.messages import await_message, send_message, send_response

from classes.TermsChecker import TermsChecker
from classes.access import AccessControl
from classes.appeal import inform_user
from classes.bans import Bans
from classes.configdata import ConfigData
from classes.configer import Configer
from classes.evidence import EvidenceController
from classes.queue import queue
from data.variables.messages import evidence_message_template
from database.transactions.ServerTransactions import ServerTransactions
from view.base.secureview import SecureView
from view.buttons.banapproval import BanApproval


class BanOptionButtons(SecureView) :

	def __init__(self) :
		super().__init__(timeout=None)
		self.wait_id = None
		self.user = None
		self.guild = None
		self.ban = None

	async def get_data(self, interaction: discord.Interaction) :
		"""Gets the user data from the embed"""
		ids = interaction.message.embeds[0].footer.text.split("-")
		print(ids)
		self.guild = interaction.guild
		self.user = interaction.client.get_user(int(ids[1]))
		if self.user is None :
			self.user = await interaction.client.fetch_user(int(ids[1]))
		self.ban = await self.guild.fetch_ban(self.user)
		self.wait_id = self.guild.id + self.user.id
		return self.guild, self.user, self.ban

	@button(label="Broadcast", custom_id="share", style=discord.ButtonStyle.success)
	async def share(self, interaction: discord.Interaction, button: button) :
		await self.disable_buttons(interaction)
		await send_response(interaction, f"Your ban has been queued for broadcasting, please wait...", ephemeral=True)
		await self.process(interaction)

	@button(label="Broadcast with proof", custom_id="share_with_proof", style=discord.ButtonStyle.success)
	async def share_with_proof(self, interaction: discord.Interaction, button: button) :
		guild, user, ban = await self.get_data(interaction)

		evidence = await await_message(interaction, evidence_message_template.format(user=user.name, ban_id=self.wait_id))
		if evidence is False :
			return
		await self.disable_buttons(interaction)
		await send_response(interaction, f"Your ban has been queued for broadcasting, please wait...", ephemeral=True)
		queue().add(self.process(interaction, evidence), priority=2)

	@button(label="Log only", custom_id="silent", style=discord.ButtonStyle.primary)
	async def silent(self, interaction: discord.Interaction, button: button) :
		await self.disable_buttons(interaction)
		await send_response(interaction, f"Your ban has been silently stored, servers will still see this ban when the user joins or if they look up the user.", ephemeral=True)
		await self.process(interaction, silent=True)

	@button(label="Log with Proof", custom_id="silent_with_proof", style=discord.ButtonStyle.primary)
	async def silent_with_proof(self, interaction: discord.Interaction, button: button) :
		guild, user, ban = await self.get_data(interaction)
		evidence = await await_message(interaction, evidence_message_template.format(user=user.name, ban_id=self.wait_id))
		if evidence is False :
			return
		await self.disable_buttons(interaction)
		await send_response(interaction, f"Your ban has been silently stored, servers will still see this ban when the user joins or if they look up the user.", ephemeral=True)
		queue().add(self.process(interaction, evidence, silent=True), priority=2)

	@button(label="Hide Ban", custom_id="hide", style=discord.ButtonStyle.danger)
	async def hidden(self, interaction: discord.Interaction, button: button) :
		await self.disable_buttons(interaction)
		await send_response(interaction, f"Your ban has been hidden, other servers can't view the ban.", ephemeral=True)
		await self.process(interaction, hidden=True)

	@button(label="reactivate buttons", custom_id="reactivate_buttons", style=discord.ButtonStyle.secondary)
	async def reactivate_buttons(self, interaction: discord.Interaction, button: button) :
		for child in self.children :
			child.disabled = False
		await interaction.message.edit(view=self)

	async def disable_buttons(self, interaction: discord.Interaction) :
		for child in self.children :
			if child.custom_id == "reactivate_buttons" :
				continue
			child.disabled = True
		await interaction.message.edit(view=self)

	async def process(self, interaction, evidence=None, hidden=False, silent=False) :
		guild, user, ban = await self.get_data(interaction)
		guild_db = ServerTransactions().get(guild.id)

		staff_member: discord.User = await self.get_staff_member(guild, user)
		message: discord.Message = interaction.message
		# check is ban has to be hidden

		if hidden :
			queue().add(Bans().add_ban(user.id, guild.id, ban.reason, staff_member.name, hidden=True), priority=2)
			await send_response(interaction, f"Ban for {user.mention} has been successfully hidden.", ephemeral=True)
			await interaction.message.delete()
			return
		# check if the ban has a checklisted word, and takes action based on action type
		checkListCheckType: str|None = None
		checkListResult: str|None = None
		checkListCheckType, checkListResult = await self.checkFlaggedTerms(ban.reason.lower())

		if isinstance(checkListCheckType, list):
			# Turn the array of words into a string
			checkListResult = ", ".join(checkListResult)


		if checkListCheckType and checkListCheckType.lower() == "block":
			await self.sendDeniedEmbed(interaction, ban, checkListResult)
			queue().add(Bans().add_ban(user.id, guild.id, ban.reason + " (HIDDEN DUE TO BLOCKLIST)", staff_member.name, approved=False, hidden=True), priority=2)
			return


		if user.bot and not checkListCheckType :
			checkListResult = "MemberLookup is a bot"
			checkListCheckType = 'review'
		word_count = len(ban.reason.split(" ")) < 4
		if word_count and ("spam" not in ban.reason.lower() or "bot" not in ban.reason.lower()) and not checkListCheckType :
			checkListResult = "Short ban reason"
			checkListCheckType = 'review'

		wait_id = Bans().create_ban_id(user.id, guild.id)
		if AccessControl().access_all(user.id) and not checkListCheckType :
			checkListResult = "Banwatch Staff Member"
			checkListCheckType = 'review'


		if checkListCheckType in ['review'] :

			channel = interaction.client.get_channel(int(os.getenv("BANS")))
			queue().add(Bans().add_ban(user.id, guild.id, ban.reason, staff_member.name, approved=False), priority=2)
			if evidence :
				queue().add(self.provide_proof(interaction, evidence), priority=2)
			queue().add(self.status(interaction.client, guild, user, "waiting_approval", ban.reason, word=checkListResult,
			                        message=message, silent=silent), priority=2)

			embed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({guild.owner})",
			                      description=f"{ban.reason}")
			embed.add_field(name="flagged word", value=checkListResult, inline=False)
			embed.set_footer(text=f"invite: {guild_db.invite} To approve it manually: /approve_ban {wait_id} ")
			queue().add(
				send_message(channel, f"<@&{os.getenv('STAFF_ROLE')}>", embed=embed,
				             view=BanApproval(interaction.client, wait_id, True, silent=silent)), priority=1)
			return

		queue().add(Bans().add_ban(user.id, guild.id, ban.reason, staff_member.name, approved=True), priority=2)

		if evidence :
			queue().add(self.provide_proof(interaction, evidence), priority=2)
		if silent :
			await send_response(interaction,
			                    f"Ban silently stored for {user.mention}! Other servers may see it when a user joins but it will not be broadcasted.",
			                    ephemeral=True)
			await interaction.message.delete()
			queue().add(inform_user(guild, user), 0)

			return
		embed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({guild.owner})",
		                      description=f"{ban.reason}")
		embed.set_footer(text=f"Server Invite: {guild_db.invite} Staff member: {staff_member} ban ID: {wait_id}")
		queue().add(Bans().check_guilds(interaction, interaction.client, guild, user, embed, wait_id), priority=2)
		queue().add(self.status(interaction.client, guild, user), priority=0)


	async def provide_proof(self, interaction, evidence) :
		if not evidence :
			return
		channel = interaction.client.get_channel(int(os.getenv("BANS")))
		queue().add(EvidenceController.add_evidence(interaction, evidence, self.wait_id, self.user), priority=2)

	async def check_checklisted_words(self, ban) :
		found = None
		checklist: list = await Configer.get_checklist()
		if checklist :
			for word in checklist :
				if word.lower() in ban.reason.lower() :
					found = word
		return found

	async def get_staff_member(self, guild, user) :
		async for entry in guild.audit_logs(limit=100, action=discord.AuditLogAction.ban) :
			if entry.target.id == user.id :
				if entry.user.bot :
					return guild.owner
				return entry.user

	async def verification_notification(self, banreason, bot, guild, user, word, message: discord.Message = None,
	                                    silent=False) :
		modchannel_id = ConfigData().get_key(guild.id, "modchannel")
		modchannel = bot.get_channel(int(modchannel_id))
		supportguild = bot.get_guild(bot.SUPPORTGUILD)
		support_invite = await Bans().create_invite(supportguild)
		if word in ["Short ban reason", "Banwatch Staff Member"]:
			if message :
				await message.edit(content=f"This ban has been submitted to be reviewed, we review short bans to ensure the quality of the shared bans. You don't have to do anything else!", view=None)
				return
			await send_message(modchannel,
			                   f"This ban has been submitted to be reviewed, we reviewbans to ensure the quality of the shared bans. You don't have to do anything else!")
			return

		verembed = discord.Embed(title=f"ban for {user}({user.id}) was flagged for review",
		                         description=f"{banreason}\n\n"
		                                     f"Flagged word: {word}. We review bans with serious accusations to ensure they are legitimate.")
		verembed.set_footer(
			text=f"Please supply evidence by using the /evidence add commmand, or by joining our support server (18+).\n\n{'This ban is not broadcasted on approval' if silent else None}")
		if message :
			await message.edit(content=f"-# You can join our support server by [clicking here to join]({support_invite}).",
			                   embed=verembed, view=None)
			return
		await send_message(modchannel, f"-# You can join our support server by [clicking here to join]({support_invite}).",
		                   embed=verembed)

	async def status(self, bot, guild, user: discord.User, status="queued", banreason=None, word=None, message=None,
	                 silent=False) :
		"""informs user is the ban has been approved or is in queue"""
		modchannel = ConfigData().get_key(guild.id, "modchannel")
		channel = bot.get_channel(int(modchannel))
		if status == "waiting_approval" :
			await self.verification_notification(banreason, bot, guild, user, word=word, message=message, silent=silent)
			return
		message: discord.Message = await channel.send(f"Your ban for {user.mention} is currently: {status}.")
		queue().add(
			message.edit(content=f"Your ban for {user.mention} has been successfully broadcasted to other servers."))


	async def sendDeniedEmbed(self, interaction, ban: discord.BanEntry, checkListResult: str):
		embed = discord.Embed(
			title=f"Your ban for {ban.user.name}({ban.user.id}) has been denied.)",
			description=f"{ban.user.mention} has been denied as it contains content we do not allow to be shared. Please reban this user without the content.",
		)
		embed.add_field(name="Offending content", value=checkListResult)
		embed.set_footer(text="To prevent abuse of the system, we try to filter out certain words. Please open a ticket in our support server if you need help.")
		await send_message(interaction.channel, embed=embed)


	async def checkFlaggedTerms(self, target):
		checks = {
			"reviewCheck"      : TermsChecker("review", target),
			"countReviewCheck" : TermsChecker("countreview", target),
			"blockCheck"       : TermsChecker("block", target),
			"blockReviewCheck" : TermsChecker("countblock", target),
		}
		for key, val in checks.items() :
			val: TermsChecker
			if val.getReviewStatus() == "":
				continue
			return val.getResults()
		return None, None

	async def on_error(self, interaction: Interaction, error: Exception, item: Item[Any], /) -> None:
		await send_response(interaction, f"An error has occurred: {error}")