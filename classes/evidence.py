import asyncio
import io
import logging
import os

import discord
import requests
from sqlalchemy.dialects.postgresql import array

from classes.bans import Bans
from classes.queue import queue
from classes.support.discord_tools import send_message, send_response
from database.current import Proof
from database.databaseController import BanDbTransactions, ProofDbTransactions


class EvidenceController() :
	@staticmethod
	async def add_evidence(interaction: discord.Interaction, evidence, ban_id, user) :
		await asyncio.sleep(5)
		ban = BanDbTransactions().get(ban_id, override=True)
		if ban is None :
			queue().add(send_response(interaction,
			                          f"Ban ID {ban_id} not found, please check if the user is banned. If this error persists please open a ticket in the support server."), priority=2)
			return
		attachments, result = await EvidenceController.create_evidence_entry(ban_id, evidence, interaction, user)
		if result is None :
			logging.error(f"Failed to create proof for {ban_id}")
			return
		queue().add(send_message(interaction.channel, f"Proof for {user.name}({user.id}) has been added to the evidence channel."), priority=2)
		del evidence
		ban_entry, embed = await Bans().find_ban_record(interaction.client, ban_id)
		result: Proof
		if ban.approved is False or ban.hidden is True :
			approval_channel = int(os.getenv('BANS'))
			channel = interaction.client.get_channel(approval_channel)
			queue().add(send_message(channel,
			                         f"Ban ID {ban_id} has been updated with new evidence:\n"
			                         f"{result.proof}\n\n"
			                         f"{'**This ban is currently hidden, use /staff banvisibility ban_id: hide: if you wish to edit visibility status**' if ban.hidden else ''}", files=attachments))
			return
		if ban_entry is None :
			logging.info(f"pre-banwatch ban {ban_id} added evidence: {result.id}")
			return
		thread = await ban_entry.fetch_thread()
		if thread is None :
			thread = await ban_entry.create_thread(name=f"Evidence for {user.name}({user.id})")
		queue().add(thread.send(f"Ban ID {ban_id} has been updated with new evidence:\n{result.proof}", files=attachments))

	@staticmethod
	async def create_evidence_entry(ban_id, evidence: discord.Message, interaction, user) :
		snapshot_message = None
		attachments = [await a.to_file() for a in evidence.attachments]
		evidence_channel = interaction.client.get_channel(int(os.getenv("EVIDENCE")))
		if evidence.message_snapshots:
			snapshot_attach = [await a.to_file() for a in evidence.message_snapshots[0].attachments]
			attachments.extend(snapshot_attach)
			snapshot_message = evidence.message_snapshots[0].content
		reason = f"Evidence for {ban_id}: \n```{evidence.content} {f'forwarded: {snapshot_message}' if snapshot_message else ''}```"
		stored = await send_message(evidence_channel, reason, files=attachments)
		attachments = [await a.to_file() for a in stored.attachments]
		attachments_urls = [a.url for a in stored.attachments]
		result = ProofDbTransactions().add(ban_id=ban_id, user_id=user.id, proof=f"{evidence.content} {f'forwarded: {snapshot_message}' if snapshot_message else ''}",
		                                   attachments=attachments_urls)
		try:
			await evidence.delete()
		except discord.Forbidden:
			await send_message(interaction.channel, "Failed to clean up evidence in channel, please grant me the ability to manage messages.")
		return attachments, result

	async def retrieve_proof(self, evidence: Proof) :
		"""Gets image from discord CDN and then creates a discord.File"""
		if len(evidence.get_attachments()) <= 0 :
			return None
		attachments = []
		for i, url in enumerate(evidence.get_attachments()) :
			response = requests.get(url, stream=True)
			if response.status_code != 200 :
				print("Could not fetch image")
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
