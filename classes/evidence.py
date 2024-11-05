import io
import os

import discord
import requests
import logging

from classes.bans import Bans
from classes.queue import queue
from classes.support.discord_tools import send_message, send_response
from database.current import Proof
from database.databaseController import BanDbTransactions, ProofDbTransactions


class EvidenceController() :
	@staticmethod
	async def add_evidence(interaction: discord.Interaction, evidence, ban_id, user) :
		ban = BanDbTransactions().get(ban_id)
		if ban is None :
			queue().add(send_response(interaction,
			                          f"Ban ID {ban_id} not found, please check if the user is banned. If this error persists please open a ticket in the support server."))
			return
		attachments, result = await EvidenceController.create_evidence_entry(ban_id, evidence, interaction, user)
		if result is not None :
			logging.error(f"Failed to create proof for {ban_id}")
			return
		ban_entry, embed = await Bans().find_ban_record(interaction.client, ban_id)
		result: Proof
		if ban.approved is False :
			approval_channel = int(os.getenv('BANS'))
			channel = interaction.client.get_channel(approval_channel)
			queue().add(send_message(channel,
			                         f"Ban ID {ban_id} has been updated with new evidence:\n"
			                         f"{evidence.content}", files=attachments))
			queue().add(
				send_message(interaction.channel, f"Proof for {user.name}({user.id}) has been added to the evidence channel."))
			await evidence.delete()
		if ban_entry is None :
			logging.info(f"pre-banwatch ban {ban_id} added evidence: {result.id}")
			return
		thread = await ban_entry.fetch_thread()
		if thread is None :
			thread = await ban_entry.create_thread(name=f"Evidence for {user.name}({user.id})")
		queue().add(thread.send(f"{evidence.content}", files=attachments))
		await evidence.delete()

	@staticmethod
	async def create_evidence_entry(ban_id, evidence, interaction, user) :
		attachments = [await a.to_file() for a in evidence.attachments]
		evidence_channel = interaction.client.get_channel(int(os.getenv("EVIDENCE")))
		stored = await send_message(evidence_channel, f"Evidence for {ban_id}: \n```{evidence.content}```",
		                            files=attachments)
		attachments = [await a.to_file() for a in stored.attachments]
		attachments_urls = [a.url for a in stored.attachments]
		result = ProofDbTransactions().add(ban_id=ban_id, user_id=user.id, proof=evidence.content,
		                                   attachments=attachments_urls)
		return attachments, result

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

	async def send_proof(self, interaction, entries, id) :
		if not entries :
			await send_response(interaction, f"Ban for {id} not found!")
			return
		await send_response(interaction, f"Succesfully retrieved proof!", ephemeral=True)
		await send_message(interaction.channel, f"## __Proof for {id}__")
		evidence: Proof
		for evidence in entries :
			attachments = await EvidenceController().retrieve_proof(evidence)
			content = (f"**{evidence.ban_id}**:"
			           f"\n**ban reason**: {evidence.ban.reason}"
			           f"\n**Provided Proof**: {evidence.proof}")
			await send_message(interaction.channel, content, files=attachments)
