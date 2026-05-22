
from typing import List

import discord

from classes.queue import queue
from database.current import Warnings
from database.transactions.WarningEvidenceTransactions import WarningEvidenceTransactions
from database.transactions.WarningTransactions import WarningTransactions


class WarningEvidence():

	def __init__(self, warning: Warnings | int):
		if isinstance(warning, int):
			self.warning = WarningTransactions().get_id(warning)
		else :
			self.warning = warning



	async def create_evidence(self,  message: discord.Message, evidence_channel: discord.TextChannel) -> bool:
		# We check if the warning exists
		if not WarningTransactions().exists(self.warning.id):
			return False
		# We create the message in the evidence channel
		msg = await self.create_message(message, evidence_channel)
		# We create the record
		WarningEvidenceTransactions().add(self.warning.id, self.warning.user_id, self.warning.guild_id, msg.id)
		# We return success
		await message.channel.send(f"{message.author.mention} has added **Evidence** to warning {self.warning.id}, view it here: {msg.jump_url}")
		return True


	async def fetch_evidence(self, evidence_channel: discord.TextChannel,  target_channel: discord.TextChannel) -> bool:
		# fetch evidence
		evidence_list = WarningEvidenceTransactions().get_warning(self.warning.id)
		# forward it to the channel
		for evidence in evidence_list:
			message = await evidence_channel.fetch_message(evidence.message_id)
			queue().add(message.forward(target_channel))
		# return successful
		return True


	async def create_message(self, message: discord.Message, evidence_channel: discord.TextChannel) -> discord.Message :
		"""
		Clones a message (or a forwarded message snapshot) into the target evidence channel.
		"""
		# 1. Handle Forwarded Messages (Snapshots) if they exist
		if hasattr(message, 'snapshots') and message.snapshots :
			# We take the first snapshot (Discord currently only supports one per forward)
			snapshot = message.snapshots[0]
			content = snapshot.content
			embeds = snapshot.embeds
			attachments = snapshot.attachments

			# Optional: Add a header indicating this was a forwarded message
			header = f"↪️ **Forwarded Message** (Original by {snapshot.author.mention if snapshot.author else 'Unknown'}):\n"
			content = header + content if content else header
		else :
			# 2. Handle a standard message
			content = message.content
			embeds = message.embeds
			attachments = message.attachments

		# 3. Process files and embeds so they are ready to send
		files = await self._prepare_attachments(attachments)
		cleaned_embeds = self._prepare_embeds(embeds)

		# 4. Send the cloned message to the evidence channel
		cloned_message = await evidence_channel.send(
			content=f"Evidence for warning {self.warning.id}:\n" + content,
			embeds=cleaned_embeds,
			files=files
		)

		# Clean up files from memory after sending
		for file in files :
			file.close()

		return cloned_message

	async def _prepare_attachments(self, attachments: List[discord.Attachment]) -> List[discord.File] :
		"""Downloads attachments into memory bytes so they can be re-uploaded."""
		files = []
		for attachment in attachments :
			# Convert the attachment into a discord.File object using its bytes
			file_bytes = await attachment.read()
			from io import BytesIO
			file_io = BytesIO(file_bytes)
			files.append(discord.File(file_io, filename=attachment.filename))
		return files

	def _prepare_embeds(self, embeds: List[discord.Embed]) -> List[discord.Embed] :
		"""Ensures embeds are deep-copied properly to avoid mutation issues."""
		cleaned_embeds = []
		for embed in embeds :
			# We convert to dict and back to ensure a clean copy is made
			embed_dict = embed.to_dict()

			# Remove types that Discord API doesn't allow bots to explicitly send
			if 'type' in embed_dict :
				del embed_dict['type']

			cleaned_embeds.append(discord.Embed.from_dict(embed_dict))
		return cleaned_embeds







