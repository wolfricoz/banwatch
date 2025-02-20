import os

import discord
from discord.ui import View, button

from classes.access import AccessControl
from classes.bans import Bans
from classes.configer import Configer
from classes.evidence import EvidenceController
from classes.queue import queue
from classes.support.discord_tools import await_message, send_message
from data.variables.messages import evidence_message_template
from database.databaseController import ServerDbTransactions
from view.buttons.banapproval import BanApproval


class BanOptionButtons(View) :

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
		if self.user is None:
			self.user = await interaction.client.fetch_user(int(ids[1]))
		self.ban = await self.guild.fetch_ban(self.user)
		self.wait_id = self.guild.id + self.user.id
		return self.guild, self.user, self.ban

	@button(label="Share", custom_id="share", style=discord.ButtonStyle.success)
	async def share(self, interaction: discord.Interaction, button: button) :
		await self.process(interaction)

	@button(label="Share with proof", custom_id="share_with_proof", style=discord.ButtonStyle.success)
	async def share_with_proof(self, interaction: discord.Interaction, button: button) :
		guild, user, ban = await self.get_data(interaction)

		evidence = await await_message(interaction, evidence_message_template.format(user=user.name, ban_id=self.wait_id))
		if evidence is False:
			return
		queue().add(self.process(interaction, evidence), priority=2)

	@button(label="Silent", custom_id="silent", style=discord.ButtonStyle.primary)
	async def silent(self, interaction: discord.Interaction, button: button) :
		await self.process(interaction, silent=True)

	@button(label="Silent with proof", custom_id="silent_with_proof", style=discord.ButtonStyle.primary)
	async def silent_with_proof(self, interaction: discord.Interaction, button: button) :
		guild, user, ban = await self.get_data(interaction)
		evidence = await await_message(interaction, evidence_message_template.format(user=user.name, ban_id=self.wait_id))
		if evidence is False:
			return
		queue().add(self.process(interaction, evidence, silent=True), priority=2)

	@button(label="Hide", custom_id="hide", style=discord.ButtonStyle.danger)
	async def hidden(self, interaction: discord.Interaction, button: button) :
		await self.process(interaction, hidden=True)

	async def process(self, interaction, evidence= None, hidden=False, silent=False) :
		guild, user, ban = await self.get_data(interaction)
		guild_db = ServerDbTransactions().get(guild.id)

		staff_member: discord.User = await self.get_staff_member(guild, user)
		message: discord.Message = interaction.message
		# check is ban has to be hidden
		if hidden :
			queue().add(Bans().add_ban(user.id, guild.id, ban.reason, staff_member.name, hidden=True), priority=2)
			await interaction.response.send_message(f"Ban for {user.mention} has been successfully hidden.", ephemeral=True)
			await interaction.message.delete()
			return
		# Additional check to see if user is a bot; technically not needed.
		# check if the ban has a checklisted word
		checklist_check = await self.check_checklisted_words(ban)
		if user.bot and not checklist_check:
			checklist_check = "User is a bot"
		word_count = len(ban.reason.split(" ")) < 4
		if word_count and not checklist_check:
			checklist_check = "Short ban reason"
		wait_id = Bans().create_ban_id(user.id, guild.id)
		if  AccessControl().access_all(user) and not checklist_check:
			checklist_check = "Banwatch Staff Member"
		if checklist_check  :

			channel = interaction.client.get_channel(int(os.getenv("BANS")))
			queue().add(Bans().add_ban(user.id, guild.id, ban.reason, staff_member.name, approved=False), priority=2)
			if evidence :
				queue().add(self.provide_proof(interaction, evidence), priority=2)
			queue().add(self.status(interaction.client, guild, user, "waiting_approval", ban.reason, word=checklist_check,
			                        message=message, silent=silent))
			embed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({guild.owner})",
			                      description=f"{ban.reason}")
			embed.add_field(name="flagged word", value=checklist_check, inline=False)
			embed.set_footer(text=f"invite: {guild_db.invite} To approve it manually: /approve_ban {wait_id} ")
			queue().add(
				send_message(channel, f"<@&{os.getenv('STAFF_ROLE')}>", embed=embed, view=BanApproval(interaction.client, wait_id, True, silent=silent)))
			return

		queue().add(Bans().add_ban(user.id, guild.id, ban.reason, staff_member.name, approved=True), priority=2)
		if evidence:
			queue().add(self.provide_proof(interaction, evidence), priority=2)
		if silent :
			return
		embed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({guild.owner})",
		                      description=f"{ban.reason}")
		embed.set_footer(text=f"Server Invite: {guild_db.invite} Staff member: {staff_member} ban ID: {wait_id}")
		queue().add(Bans().check_guilds(interaction, interaction.client, guild, user, embed, wait_id))
		queue().add(self.status(interaction.client, guild, user), priority=0)

	async def provide_proof(self, interaction, evidence) :
		if not evidence :
			return
		channel = interaction.client.get_channel(int(os.getenv("BANS")))
		queue().add(EvidenceController.add_evidence(interaction, evidence, self.wait_id, self.user))

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
		modchannel_id = await Configer.get(guild.id, "modchannel")
		modchannel = bot.get_channel(int(modchannel_id))
		supportguild = bot.get_guild(bot.SUPPORTGUILD)
		support_invite = await Bans().create_invite(supportguild)
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
		modchannel = await Configer.get(guild.id, "modchannel")
		channel = bot.get_channel(int(modchannel))
		if status == "waiting_approval" :
			await self.verification_notification(banreason, bot, guild, user, word=word, message=message, silent=silent)
			return
		message: discord.Message = await channel.send(f"Your ban for {user.mention} is currently: {status}.")
		queue().add(
			message.edit(content=f"Your ban for {user.mention} has been successfully broadcasted to other servers."))
