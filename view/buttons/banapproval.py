import discord
from discord.ui import View
from discord_py_utilities.messages import send_message, send_response

from classes.appeal import inform_user
from classes.bans import Bans
from classes.configdata import ConfigData
from classes.evidence import EvidenceController
from classes.queue import queue
from database.databaseController import BanDbTransactions, ProofDbTransactions
from view.modals.inputmodal import send_modal


class BanApproval(View) :
	bot = None

	def __init__(self, bot, wait_id, create_thread=False, silent=False) :
		super().__init__(timeout=None)
		self.bot = bot
		self.wait_id = wait_id
		self.create_thread = create_thread
		self.silent = silent

	@discord.ui.button(label="Approve with Proof (Verify)", style=discord.ButtonStyle.success, custom_id="verify_ban")
	async def verify(self, interaction: discord.Interaction, button: discord.ui.Button) :
		await interaction.response.defer(ephemeral=True)
		if self.bot is None or self.wait_id is None :
			await send_response(interaction, "Error: The bot has restarted, the data of this button was lost", ephemeral=True)
			return
		ban_entry = BanDbTransactions().get(self.wait_id, override=True)
		if ban_entry is None :
			await send_response(interaction, "Ban not found", ephemeral=True)
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
		await send_response(interaction, 
			f"Approved `{interaction.message.embeds[0].title}`   with proof by {interaction.user.mention}! {'Silent option was true, ban not broadcast' if self.silent else ''}",
			ephemeral=False)
		await self.update_embed(interaction)
		if self.silent :
			queue().add(inform_user(guild, user), 0)

			return
		await Bans().check_guilds(None, self.bot, guild, user, banembed, self.wait_id, self.create_thread, verified=True)

	@discord.ui.button(label="Approve without Proof", style=discord.ButtonStyle.success, custom_id="approve_ban")
	async def approve_no_proof(self, interaction: discord.Interaction, button: discord.ui.Button) :
		await interaction.response.defer(ephemeral=True)
		if self.bot is None or self.wait_id is None :
			await send_response(interaction, "Error: The bot has restarted, the data of this button was lost", ephemeral=True)
			return
		ban_entry = BanDbTransactions().get(self.wait_id)
		if ban_entry is None :
			await send_response(interaction, "Ban not found", ephemeral=True)
			return
		guild, user, reason = await self.get_ban_data(ban_entry)
		owner = guild.owner
		banembed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({owner})",
		                         description=f"{reason}")
		banembed.set_footer(text=f"Server Invite: {ban_entry.guild.invite} Server Owner: {owner} ban ID: {self.wait_id} ")
		await send_response(interaction, 
			f"Approved `{interaction.message.embeds[0].title}`   without proof by {interaction.user.mention}! {'Silent option was true, ban not broadcast' if self.silent else ''}",
			ephemeral=False)
		await self.update_embed(interaction, "approve")
		if self.silent :
			queue().add(inform_user(guild, user), 0)

			return
		await Bans().check_guilds(None, self.bot, guild, user, banembed, self.wait_id, False)

	@discord.ui.button(label="Inform Server", style=discord.ButtonStyle.primary, custom_id="request_evidence")
	async def request_evidence(self, interaction: discord.Interaction, button: discord.ui.Button) :
		reason = await send_modal(interaction, confirmation="Thank you for providing a reason",
		                          title="What evidence do we require?")
		if not reason :
			return None
		ban_entry = BanDbTransactions().get(self.wait_id, override=True)
		if ban_entry is None :
			return await send_response(interaction, "Ban not found")
		guild: discord.Guild = interaction.client.get_guild(ban_entry.gid)
		user: discord.User = await interaction.client.fetch_user(ban_entry.uid)
		modchannel = await ConfigData().get_channel(guild)

		content = f"The banwatch team requests that you add more evidence to user {user}({user.id}), you can do this by joining our support guild or by using `/evidence add user:{user.id}`."
		embed = discord.Embed(title=f"Evidence request for ban {ban_entry.ban_id}", description=content)
		embed.add_field(name=f"Request reason", value=reason)
		await send_message(modchannel, embed=embed)
		await send_response(interaction, f"{guild.name} has been notified with reason:\n{reason}")
		return None

	@discord.ui.button(label="view evidence", style=discord.ButtonStyle.primary, custom_id="view_evidence")
	async def view_evidence(self, interaction: discord.Interaction, button: discord.ui.Button) :
		ban_entry = BanDbTransactions().get(self.wait_id, override=True)
		if ban_entry is None :
			await send_response(interaction, "Ban not found", ephemeral=True)
			return
		guild, user, reason = await self.get_ban_data(ban_entry)
		user_id = user.id
		entries = ProofDbTransactions().get(ban_id=self.wait_id)
		await EvidenceController().send_proof(interaction, entries, self.wait_id)

	@discord.ui.button(label="Hide & Inform", style=discord.ButtonStyle.danger, custom_id="deny_broadcast")
	async def hide(self, interaction: discord.Interaction, button: discord.ui.Button) :
		deny_reason = await send_modal(interaction, confirmation="Thank you for providing a reason", title="Denial Reason",
		                               max_length=1000)
		if self.bot is None or self.wait_id is None :
			await send_response(interaction, "Error: The bot has restarted, the data of this button was lost", ephemeral=True)
			return
		ban_entry = BanDbTransactions().get(self.wait_id, override=True)
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
		BanDbTransactions().update(self.wait_id, approved=True, hidden=True)
		await self.update_embed(interaction, "hide")
		await send_response(interaction, 
			f"Hidden `{interaction.message.embeds[0].title}`  with reason `{deny_reason}` by {interaction.user.mention}!",
			ephemeral=False)
		await denial_channel.send(embed=banembed)
		if mod_channel :
			await mod_channel.send(embed=banembed)
		# await send_response(interaction, f"Ban Hidden: \n `{deny_reason}`", ephemeral=True)

	@discord.ui.button(label="Hide Ban", style=discord.ButtonStyle.danger, custom_id="deny_silent")
	async def hidesilent(self, interaction: discord.Interaction, button: discord.ui.Button) :
		if self.bot is None or self.wait_id is None :
			await send_response(interaction, "Error: The bot has restarted, the data of this button was lost", ephemeral=True)
			return
		ban_entry = BanDbTransactions().get(self.wait_id, override=True)
		if ban_entry is None :
			await send_response(interaction, "Ban not found", ephemeral=True)
			return
		guild, user, reason = await self.get_ban_data(ban_entry)
		owner = guild.owner
		denial_channel = self.bot.get_channel(self.bot.DENIALCHANNEL)
		banembed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({owner})",
		                         description=f"{reason}")
		banembed.set_footer(text=f"Ban Hidden")
		BanDbTransactions().update(self.wait_id, approved=True, hidden=True)
		await self.update_embed(interaction, "hidesilent")
		await send_response(interaction,
			f"Silently Hidden `{interaction.message.embeds[0].title}`  by {interaction.user.mention}!")
		await denial_channel.send(embed=banembed)

	async def update_embed(self, interaction, action="verify") :
		self.update_buttons(action)
		embed: discord.Embed = interaction.message.embeds[0]
		embed.set_footer(text=f"action `{action}` was performed by {interaction.user}")
		embed.add_field(name="Banwatch ID", value=self.wait_id, inline=False)
		await interaction.message.edit(embed=interaction.message.embeds[0], view=self)

	async def get_ban_data(self, ban_entry) :
		return self.bot.get_guild(ban_entry.gid), await self.bot.fetch_user(ban_entry.uid), ban_entry.reason

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
			case "approve" :
				self.approve_no_proof.style = discord.ButtonStyle.success
			case "verify" :
				self.verify.style = discord.ButtonStyle.success
