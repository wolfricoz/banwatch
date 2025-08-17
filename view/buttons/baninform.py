import io
import logging
import re

import discord
import requests
from discord_py_utilities.bans import ban_member, ban_user
from discord_py_utilities.messages import send_message, send_response

from database.current import Proof
from database.databaseController import BanDbTransactions, ProofDbTransactions
from view.base.secureview import SecureView
from view.buttons.confirm import Confirm
from view.modals.inputmodal import send_modal


class BanInform(SecureView) :
	bot = None

	def __init__(self, ban_class, ban_id= None) :
		super().__init__(timeout=None)
		self.ban_class = ban_class
		self.ban_id = ban_id
		if ban_id is None:
			return
		entries = ProofDbTransactions().get(ban_id=ban_id)
		if not entries:
			self.evidence.disabled = True


	async def get_ban_id(self, interaction: discord.Interaction) :
		embed = interaction.message.embeds[0]
		match = re.search(r'ban ID: (\w+)', embed.footer.text)
		return match.group(1) if match else None

	@discord.ui.button(label="Ban with Reason", style=discord.ButtonStyle.success, custom_id="ban_user")
	async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button) :
		ban_id = await self.get_ban_id(interaction)
		if ban_id is None :
			logging.error(f"Could not find ban id in {interaction.guild.name}.")
			await send_response(interaction, f"[REGEX ERROR] Could not retrieve ban_id!")
		entry = BanDbTransactions().get(ban_id)
		user = interaction.client.get_user(entry.uid)
		guild = interaction.client.get_guild(entry.gid)
		reason_modal = await send_modal(interaction, "Thank you for submitting your reason!", "Ban Reason")
		await ban_user(interaction, user, "", f"Cross-ban from {guild.name} with ban id: {ban_id} with reason: {reason_modal}", self.ban_class, clean=False)

	@discord.ui.button(label="Cross-Ban", style=discord.ButtonStyle.success, custom_id="cross_ban_user")
	async def cross_ban_button(self, interaction: discord.Interaction, button: discord.ui.Button) :
		ban_id = await self.get_ban_id(interaction)
		if ban_id is None :
			logging.error(f"Could not find ban id in {interaction.guild.name}.")
			await send_response(interaction, f"[REGEX ERROR] Could not retrieve ban_id!")
		entry = BanDbTransactions().get(ban_id)
		user = interaction.client.get_user(entry.uid)
		guild = interaction.client.get_guild(entry.gid)
		result = await Confirm().send_confirm(interaction, message=f'Are you sure you want to cross-ban this user with the ban from {guild.name}?')
		if not result:
			await send_response(interaction, "Cancelled", ephemeral=True)
			return
		reason = f"Cross-ban from {guild.name} with ban id: {ban_id}"
		await ban_member(self.ban_class, interaction, user, reason, days=0)
		await send_response(interaction, f"Banning user")

	@discord.ui.button(label="view evidence", style=discord.ButtonStyle.primary, custom_id="evidence")
	async def evidence(self, interaction: discord.Interaction, button: discord.ui.Button) :
		ban_id = await self.get_ban_id(interaction)
		entries = ProofDbTransactions().get(ban_id=ban_id)
		await self.send_proof(interaction, entries, ban_id)

	async def retrieve_proof(self, evidence: Proof) :
		"""Gets image from discord CDN and then creates a discord.File"""
		if len(evidence.get_attachments()) <= 0 :
			return None
		attachments = []
		for i, url in enumerate(evidence.get_attachments()) :
			response = requests.get(url, stream=True)
			if response.status_code != 200 :
				continue
			image_data = io.BytesIO(response.content)
			image_data.seek(0)
			attachments.append(discord.File(image_data, filename=f"image_{i}.jpg"))
		return attachments

	async def send_proof(self, interaction: discord.Interaction, entries: list, ban_id: int) :
		if not entries :
			await send_response(interaction, f"No proof available for ban id: {ban_id}! Please reach out to the server where the user is banned. ")
			return
		await send_response(interaction, f"Succesfully retrieved proof!", ephemeral=True)
		await send_message(interaction.channel, f"## __Proof for {ban_id}__")
		evidence: Proof
		for evidence in entries :
			proof = '\n'.join(evidence.get_attachments())
			content = (f"**{evidence.ban_id}**:"
			           f"\n**ban reason**: {evidence.ban.reason}"
			           f"\n**Provided Proof**: {evidence.proof}"
			           f"\n**attachments:**\n {proof}")
			await send_message(interaction.channel, content)
