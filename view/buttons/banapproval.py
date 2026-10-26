import logging
import time

import discord
from discord_py_utilities.messages import send_message, send_response

from classes.appeal import inform_user
from classes.ban.ban_channel import UNSET, resolve_ban_channel, warn_missing_ban_channel
from classes.bans import Bans
from classes.configdata import ConfigData
from classes.evidence import EvidenceController
from classes.queue import queue
from database.transactions.BanTransactions import BanTransactions
from database.transactions.ProofTransactions import ProofTransactions
from view.base.secureview import SecureView
from view.modals.inputmodal import send_modal
from view.multiselect.selectinform import SelectInform
from view.multiselect.selectreason import SelectReason
from view.v2.EvidenceSubmission import EvidenceUI


class BanApproval(SecureView) :
	bot = None

	def __init__(self, bot, wait_id, create_thread=False, silent=False) :
		super().__init__(timeout=None)
		self.bot = bot
		self.wait_id = wait_id
		self.create_thread = create_thread
		self.silent = silent

	# ============================================================
	@discord.ui.button(label="Approve with Proof (Verify)", style=discord.ButtonStyle.success, custom_id="verify_ban")
	async def verify(self, interaction: discord.Interaction, button: discord.ui.Button) :
		await interaction.response.defer(ephemeral=True)
		if self.bot is None or self.wait_id is None :
			await send_response(interaction, "Error: The bot has restarted, the data of this button was lost", ephemeral=True)
			return
		ban_entry = BanTransactions().get(self.wait_id, override=True)
		if ban_entry is None :
			await send_response(interaction, "Ban not found", ephemeral=True)
			return
		if ban_entry.approved :
			# A bulk approval (/staff approve_pending) leaves these review messages live in the ban
			# channel with working buttons. Without this guard a second press runs check_guilds
			# again and broadcasts the ban to the whole network twice.
			await send_response(interaction, "This ban has already been handled and is no longer pending.",
			                    ephemeral=True)
			return
		# noinspection PyTypeChecker,PydanticTypeChecker
		if len(ban_entry.proof) < 1 :
			await send_response(interaction, "No evidence found, please add evidence and try again", ephemeral=True)
			return
		guild, user, reason = await self.get_ban_data(ban_entry)
		owner = guild.owner
		banembed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({owner})",
		                         description=f"{reason}")
		banembed.add_field(name="Banwatch Verified", value="This ban was verified by banwatch staff")
		banembed.set_footer(text=f"Server Invite: {ban_entry.guild.invite} Server Owner: {owner} ban ID: {self.wait_id}. ")
		queue().add(send_response(interaction,
		                          f"Approved `{interaction.message.embeds[0].title}`   with proof by {interaction.user.mention}! {'Silent option was true, ban not broadcast' if self.silent else ''}",
		                          ephemeral=False), priority=2)
		await self.update_embed(interaction)
		queue().add(self.send_feedback(), priority=0)

		if self.silent :
			queue().add(inform_user(guild, user), 0)

			return
		await Bans().check_guilds(None, self.bot, guild, user, banembed, self.wait_id, self.create_thread, verified=True)

	# ============================================================
	@discord.ui.button(label="Approve without Proof", style=discord.ButtonStyle.success, custom_id="approve_ban")
	async def approve_no_proof(self, interaction: discord.Interaction, button: discord.ui.Button) :
		await interaction.response.defer(ephemeral=True)
		if self.bot is None or self.wait_id is None :
			await send_response(interaction, "Error: The bot has restarted, the data of this button was lost", ephemeral=True)
			return
		await self.update_embed(interaction, "approve")

		queue().add(self.approve_handler(interaction), priority=2)

	# ============================================================
	@discord.ui.button(label="Inform Server", style=discord.ButtonStyle.primary, custom_id="request_evidence")
	async def request_evidence(self, interaction: discord.Interaction, button: discord.ui.Button) :
		"""Hides the ban until the server provides evidence and tells them why, using a preset or custom message.

		Evidence submitted through the request puts the ban back in this queue (see EvidenceController.add_evidence).
		"""
		if self.bot is None or self.wait_id is None :
			await send_response(interaction, "Error: The bot has restarted, the data of this button was lost", ephemeral=True)
			return
		ban_entry = BanTransactions().get(self.wait_id, override=True)
		if ban_entry is None :
			await send_response(interaction, "Ban not found", ephemeral=True)
			return
		if ban_entry.approved :
			await send_response(interaction, "This ban has already been handled and is no longer pending.",
			                    ephemeral=True)
			return

		view = SelectInform()
		await send_response(interaction, "Select the message to send to the server.", view=view, ephemeral=True)
		if await view.wait() or view.interaction is None :
			# Timed out without a selection.
			return
		message = view.get_message()
		# The select interaction is the only fresh token at this point, so the custom modal has to open on it.
		if message == "custom" :
			message = await send_modal(view.interaction, confirmation="Thank you for providing a reason",
			                           title="What evidence do we require?")
		else :
			await view.interaction.response.defer()
		if not message :
			await self.reply(interaction, "No message was provided, the server was not informed.")
			return

		guild, user, reason = await self.get_ban_data(ban_entry)
		owner = guild.owner
		BanTransactions().update(self.wait_id, approved=True, hidden=True)
		await self.update_embed(interaction, "inform")
		await send_response(interaction,
		                    f"Hidden `{interaction.message.embeds[0].title}` until evidence is provided, informed by {interaction.user.mention} with:\n{message}",
		                    ephemeral=False)

		banembed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({owner})",
		                         description=f"{reason}")
		banembed.set_footer(text=f"Ban hidden until evidence is provided: {message}"[:2048])
		denial_channel = self.bot.get_channel(self.bot.DENIALCHANNEL)
		if denial_channel :
			await denial_channel.send(embed=banembed)

		mod_channel = await resolve_ban_channel(guild)
		if mod_channel is None :
			await warn_missing_ban_channel(guild, problem=UNSET, source="evidence")
			await self.reply(interaction,
			                 f"{guild.name} has no usable mod channel, so the evidence request could not be delivered. The ban is still hidden.")
			return
		ui = EvidenceUI(user, guild, ban_entry.ban_id, reason, staff_reason=message, review=True)
		await ui.send_embed(mod_channel)

	# ============================================================
	@discord.ui.button(label="Alter Ban Reason", style=discord.ButtonStyle.primary, custom_id="change_reason")
	async def change_reason(self, interaction: discord.Interaction, button: discord.ui.Button) :
		if self.bot is None or self.wait_id is None :
			await send_response(interaction, "Error: The bot has restarted, the data of this button was lost", ephemeral=True)
			return
		await interaction.response.defer(ephemeral=True)

		view = SelectReason()
		await send_message(interaction.channel, "Select your reason.", view=view)
		await view.wait()
		reason = view.get_reason()
		# Picking a reason takes longer than the 3 second response window, so this button's interaction can no
		# longer open a modal. The select interaction is the only fresh token available at this point.
		if reason == "custom" :
			if view.interaction is None :
				await self.reply(interaction, "No reason was selected, the ban reason was not changed.")
				return
			reason = await send_modal(view.interaction, "What is the new reason for the ban?", "New Ban Reason")
		elif view.interaction is not None :
			await view.interaction.response.defer()

		if not reason :
			await self.reply(interaction, "No reason was provided, the ban reason was not changed.")
			return

		await Bans().change_ban_reason(self.wait_id, reason, interaction.user.global_name)
		await self.reply(interaction,
		                 f"You have changed the reason for `{interaction.message.embeds[0].description}` to `{reason}`")
		# update the embed of the message
		embed = interaction.message.embeds[0]
		embed.description = reason
		embed.add_field(name="Reason edited", value=f"Reason was edited by {interaction.user.mention}", inline=False)
		await interaction.message.edit(embed=embed, view=self)

	# ============================================================
	@discord.ui.button(label="view evidence", style=discord.ButtonStyle.primary, custom_id="view_evidence")
	async def view_evidence(self, interaction: discord.Interaction, button: discord.ui.Button) :
		ban_entry = BanTransactions().get(self.wait_id, override=True)
		if ban_entry is None :
			await send_response(interaction, "Ban not found", ephemeral=True)
			return
		guild, user, reason = await self.get_ban_data(ban_entry)
		user_id = user.id
		entries = ProofTransactions().get(ban_id=self.wait_id)
		await EvidenceController().send_proof(interaction, entries, self.wait_id)

	# ============================================================
	@discord.ui.button(label="Hide & Inform", style=discord.ButtonStyle.danger, custom_id="deny_broadcast")
	async def hide(self, interaction: discord.Interaction, button: discord.ui.Button) :
		deny_reason = await send_modal(interaction, confirmation="Thank you for providing a reason", title="Denial Reason",
		                               max_length=1000)
		if self.bot is None or self.wait_id is None :
			await send_response(interaction, "Error: The bot has restarted, the data of this button was lost", ephemeral=True)
			return
		ban_entry = BanTransactions().get(self.wait_id, override=True)
		if ban_entry is None :
			await send_response(interaction, "Ban not found", ephemeral=True)
			return
		guild, user, reason = await self.get_ban_data(ban_entry)
		owner = guild.owner
		mod_channel = guild.get_channel(int(ConfigData().get_key(guild.id, "modchannel")))
		denial_channel = self.bot.get_channel(self.bot.DENIALCHANNEL)
		banembed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({owner})",
		                         description=f"{reason}")
		banembed.set_footer(text=f"Ban Hidden: {deny_reason}")
		BanTransactions().update(self.wait_id, approved=True, hidden=True)
		await self.update_embed(interaction, "hide")
		await send_response(interaction,
		                    f"Hidden `{interaction.message.embeds[0].title}`  with reason `{deny_reason}` by {interaction.user.mention}!",
		                    ephemeral=False)
		await denial_channel.send(embed=banembed)
		if mod_channel :
			ui = EvidenceUI(user, guild, ban_entry.ban_id, reason, staff_reason=deny_reason)
			await ui.send_embed(mod_channel)

	# await send_response(interaction, f"Ban Hidden: \n `{deny_reason}`", ephemeral=True)

	# ============================================================
	@discord.ui.button(label="Hide Ban", style=discord.ButtonStyle.danger, custom_id="deny_silent")
	async def hidesilent(self, interaction: discord.Interaction, button: discord.ui.Button) :
		if self.bot is None or self.wait_id is None :
			await send_response(interaction, "Error: The bot has restarted, the data of this button was lost", ephemeral=True)
			return
		ban_entry = BanTransactions().get(self.wait_id, override=True)
		if ban_entry is None :
			await send_response(interaction, "Ban not found", ephemeral=True)
			return
		guild, user, reason = await self.get_ban_data(ban_entry)
		owner = guild.owner
		denial_channel = self.bot.get_channel(self.bot.DENIALCHANNEL)
		banembed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({owner})",
		                         description=f"{reason}")
		banembed.set_footer(text=f"Ban Hidden")
		BanTransactions().update(self.wait_id, approved=True, hidden=True)
		await self.update_embed(interaction, "hidesilent")
		await send_response(interaction,
		                    f"Silently Hidden `{interaction.message.embeds[0].title}`  by {interaction.user.mention}!")
		await denial_channel.send(embed=banembed)

	# ============================================================
	async def update_embed(self, interaction, action="verify") :
		self.update_buttons(action)
		embed: discord.Embed = interaction.message.embeds[0]
		embed.set_footer(text=f"action `{action}` was performed by {interaction.user}")
		embed.add_field(name="Banwatch ID", value=self.wait_id, inline=False)
		await interaction.message.edit(embed=interaction.message.embeds[0], view=self)

	# ============================================================
	@staticmethod
	async def reply(interaction: discord.Interaction, message: str) :
		"""Sends an ephemeral follow up on a deferred interaction, falling back to the channel if the token expired."""
		try :
			await interaction.followup.send(message, ephemeral=True)
		except discord.errors.HTTPException :
			await send_message(interaction.channel, message)

	# ============================================================
	async def get_ban_data(self, ban_entry) :
		guild = self.bot.get_guild(ban_entry.gid)
		user = self.bot.get_user(ban_entry.uid)

		if user is None :
			user = await self.bot.fetch_user(ban_entry.uid)

		return guild, user, ban_entry.reason

	# ============================================================
	async def send_feedback(self) :
		"""Notifies the origin server that its ban was approved.

		The notice itself lives on Bans so /staff approve_pending sends exactly the same message.
		"""
		await Bans().notify_origin_server(self.bot, self.wait_id, silent=self.silent)

	# ============================================================
	async def approve_handler(self, interaction: discord.Interaction) :
		start = time.time()
		ban_entry = BanTransactions().get(self.wait_id, override=True)
		if ban_entry is None :
			await send_response(interaction, "Ban not found", ephemeral=True)
			return
		if ban_entry.approved :
			# A bulk approval (/staff approve_pending) leaves these review messages live in the ban
			# channel with working buttons. Without this guard a second press runs check_guilds
			# again and broadcasts the ban to the whole network twice.
			await send_response(interaction, "This ban has already been handled and is no longer pending.",
			                    ephemeral=True)
			return
		logging.info(f"Approving ban {ban_entry.ban_id}. Time since button press: {time.time() - start} seconds")

		guild, user, reason = await self.get_ban_data(ban_entry)
		logging.info(
			f"fetched ban data for user {user} in guild {guild} with reason {reason}. Time since button press: {time.time() - start} seconds")
		owner = guild.owner
		banembed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({owner})",
		                         description=f"{reason}")
		banembed.set_footer(text=f"Server Invite: {ban_entry.guild.invite} Server Owner: {owner} ban ID: {self.wait_id} ")
		logging.info(
			f"Created embed for ban approval without proof. Time since button press: {time.time() - start} seconds")
		queue().add(send_response(interaction,
		                          f"Approved `{interaction.message.embeds[0].title}`   without proof by {interaction.user.mention}! {'Silent option was true, ban not broadcast' if self.silent else ''}",
		                          ephemeral=False), priority=2)
		queue().add(self.send_feedback(), priority=0)
		logging.info(
			f"Sent feedback for ban approval without proof. Time since button press: {time.time() - start} seconds")

		if self.silent :
			queue().add(inform_user(guild, user), 0)

			return
		queue().add(Bans().check_guilds(None, self.bot, guild, user, banembed, self.wait_id, False), priority=0)

	# ============================================================
	def update_buttons(self, selected) :
		self.hide.disabled = True
		self.view_evidence.disabled = True
		self.request_evidence.disabled = True
		self.approve_no_proof.disabled = True
		self.verify.disabled = True
		self.hidesilent.disabled = True

		self.hide.style = discord.ButtonStyle.gray
		self.request_evidence.style = discord.ButtonStyle.gray
		self.view_evidence.style = discord.ButtonStyle.gray
		self.approve_no_proof.style = discord.ButtonStyle.gray
		self.verify.style = discord.ButtonStyle.gray
		self.hidesilent.style = discord.ButtonStyle.gray
		match selected :
			case "hide" :
				self.hide.style = discord.ButtonStyle.success
			case "hidesilent" :
				self.hidesilent.style = discord.ButtonStyle.success
			case "inform" :
				self.request_evidence.style = discord.ButtonStyle.success
			case "approve" :
				self.approve_no_proof.style = discord.ButtonStyle.success
			case "verify" :
				self.verify.style = discord.ButtonStyle.success
