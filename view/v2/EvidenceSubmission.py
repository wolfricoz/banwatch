import logging

import discord
from discord_py_utilities.messages import await_message, send_response

from classes.evidence import EvidenceController
from classes.queue import queue
from data.variables.messages import evidence_message_template
from database.transactions.BanTransactions import BanTransactions


class EvidenceUI(discord.ui.LayoutView) :
	def __init__(self, user: discord.User | discord.Member, guild: discord.Guild, ban_id: str, reason: str, staff_reason: str = None) :
		super().__init__(timeout=None)
		self.guild = guild
		self.user = user
		self.ban = None
		self.ban_id = ban_id
		self.reason = reason


		container = discord.ui.Container(
			discord.ui.TextDisplay(
				content="## **Evidence Request**"
			),
			discord.ui.TextDisplay(
				content="Please submit evidence for the following ban or hide it."
			),
			discord.ui.Separator(visible=True),
			discord.ui.TextDisplay(
				content=f"### {self.user} ({self.user.id}) was banned in {self.guild} ({self.guild.owner.name})"
			),
			discord.ui.TextDisplay(
				content=f"\n{self.reason}"
			),

			accent_colour=discord.Colour.blue()
		)
		if staff_reason:
			container.add_item(discord.ui.Separator(visible=True))
			container.add_item(discord.ui.TextDisplay(
				content=f"**Staff Reason:** {staff_reason}"
			))
		container.add_item(discord.ui.Separator(visible=True))
		container.add_item(discord.ui.TextDisplay(
				content=f"-# **Ban ID:** {self.ban_id}",
			))

		self.add_item(container)

		actions = discord.ui.ActionRow()
		submit_btn = discord.ui.Button(
			custom_id="submit_evidence",
			label="Submit Evidence",
			style=discord.ButtonStyle.primary
		)
		hide_btn = discord.ui.Button(
			custom_id="hide_evidence",
			label="Hide",
			style=discord.ButtonStyle.danger
		)

		submit_btn.callback = self.submit_evidence
		hide_btn.callback = self.hide

		actions.add_item(submit_btn)
		actions.add_item(hide_btn)
		self.add_item(actions)

	async def send_embed(self, channel: discord.TextChannel) :
		await channel.send(view=self)

	async def submit_evidence(self, interaction: discord.Interaction) :
		if not self.check_perms(interaction) :
			return await send_response(interaction, f"You don't have permission for this action", ephemeral=True)
		if not await self.load_data(interaction) :
			return await send_response(interaction,
			                           f"Failed to load ban data, please try again or open a ticket in the support server if this issue persists.",
			                           ephemeral=True)
		evidence = await await_message(interaction, evidence_message_template.format(user=self.user.name,
		                                                                             ban_id=self.user.id + interaction.guild.id))
		if evidence is False :
			return None
		await send_response(interaction, f"⏳ Processing Evidence, please wait.", ephemeral=True)
		queue().add(EvidenceController.add_evidence(interaction, evidence, self.user.id + interaction.guild.id, self.user),
		            priority=2)
		return None

	async def hide(self, interaction: discord.Interaction) :
		from classes.bans import Bans as BansClass
		if not self.check_perms(interaction) :
			return await send_response(interaction, f"You don't have permission for this action", ephemeral=True)
		if not await self.load_data(interaction) :
			return await send_response(interaction,
			                           f"Failed to load ban data, please try again or open a ticket in the support server if this issue persists.",
			                           ephemeral=True)
		BanTransactions().update(self.ban, hidden=True)
		await BansClass().revoke_bans(interaction.client, self.user.id + interaction.guild.id,
		                              "Ban has been hidden by the server.")
		await send_response(interaction, f"{self.user.mention}'s ban has been hidden by {interaction.user.name}")
		return None

	async def load_data(self, interaction: discord.Interaction) -> bool :
		if not self.ban_id :
			for item in interaction.message.components :
				for component in getattr(item, "children", []) :
					content = getattr(component, "content", "")
					if content.startswith("-# **Ban ID:**") :
						self.ban_id = content.replace("-# **Ban ID:**", "").strip()
						logging.info(f"Extracted Ban ID: {self.ban_id}")
						break

		logging.info(f"Ban ID: {self.ban_id}")
		if isinstance(self.ban_id, str) :
			if not self.ban_id.isnumeric() :
				logging.info(f"not numeric ban id: {self.ban_id}")
				return False
			self.ban_id = int(self.ban_id)

		if not self.ban_id :
			logging.info("No ban ID found in the embed.")
			return False

		self.ban = BanTransactions().get(self.ban_id, override=True)
		logging.info(f"ban: {self.ban}")
		try :
			self.user = interaction.client.get_user(self.ban.uid)
			if not self.user :
				self.user = await interaction.client.fetch_user(int(self.ban.uid))
			self.guild = interaction.client.get_guild(self.ban.gid)
			if not self.guild :
				self.guild = await interaction.client.fetch_guild(self.ban.gid)
		except discord.NotFound :
			logging.info(f"User {self.user} or guild {self.guild} not found for the ban.")
			return False

		logging.info(f"load data for ban_id {self.ban_id}, ban: {self.ban}, user: {self.user}, guild: {self.guild}")
		if not self.ban or not self.user or not self.guild :
			return False

		return True

	def check_perms(self, interaction: discord.Interaction) :
		if interaction.user.guild_permissions.ban_members :
			return True
		return False
