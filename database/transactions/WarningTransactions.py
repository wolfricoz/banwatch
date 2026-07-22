import logging
from typing import List

import discord
from discord_py_utilities.messages import send_message
from sqlalchemy import select

from classes.configdata import ConfigData
from data.config.mappings import Channels
from database.current import WarningEvidence, Warnings
from database.transactions.DatabaseController import DatabaseTransactions


class WarningTransactions(DatabaseTransactions) :


	async def add(self, interaction: discord.Interaction, target: discord.Member, embed: discord.Embed, reason: str, channel: discord.TextChannel | None = None):
		with self.createsession() as session:
			if not channel:
				channel: discord.TextChannel = await ConfigData().get_channel(interaction.guild, Channels.WARNING_LOG)
			embed.add_field(name="Warned By", value=f"{interaction.user.name}({interaction.user.id})", inline=False)
			msg = await send_message(channel, embed=embed)
			warning = Warnings(user_id=target.id, guild_id=interaction.guild.id, reason=reason)
			session.add(warning)
			self.commit(session)
			logging.info(f"Warning issued to {target} ({target.id}) in {interaction.guild.name} ({interaction.guild.id}) by {interaction.user} ({interaction.user.id})")

	# ============================================================
	def count_warnings(self, user_id: int, guild_id: int) -> int:
		with self.createsession() as session:
			return session.query(Warnings).filter(Warnings.user_id == user_id, Warnings.guild_id == guild_id).count()

	# ============================================================
	def get_all(self, user_id: int, guild_id: int) -> List[Warnings]:
		with self.createsession() as session:
			return session.scalars(select(Warnings).where(Warnings.user_id == user_id, Warnings.guild_id == guild_id)).all()

	# ============================================================
	def delete_warning(self, warning_id: int):
		with self.createsession() as session:
			record = session.scalar(select(Warnings).where(Warnings.id == warning_id))
			if record is None:
				logging.warning(f"Delete warning skipped: warning {warning_id} not found")
				return False
			session.delete(record)
			self.commit(session)
			logging.info(f"Warning {warning_id} deleted for user {record.user_id} in guild {record.guild_id}")
			return True

	# ============================================================
	def get_id(self, warning_id: int) -> Warnings:
		with self.createsession() as session:
			return session.scalar(select(Warnings).where(Warnings.id == warning_id))

	# ============================================================
	def exists(self, warning_id: int) -> bool:
		with self.createsession() as session:
			return session.scalar(select(Warnings).where(Warnings.id == warning_id)) is not None

	# ============================================================
	def create_evidence(self, warning: Warnings, message: discord.Message):
		with self.createsession() as session:
			evidence = WarningEvidence(warning_id=warning.id, user_id=warning.user_id, guild_id=warning.guild_id, message_id=message.id)
			session.add(evidence)
			self.commit(session)

	# ============================================================
	def fetch_all_evidence(self, guild_id: int, user_id: int = None, warnind_id: None | int = None) -> List[WarningEvidence]:
		with self.createsession() as session:
			if user_id:
				return session.scalars(select(WarningEvidence).where(WarningEvidence.user_id == user_id, WarningEvidence.guild_id == guild_id)).all()
			if warnind_id:
				return session.scalars(select(WarningEvidence).where(WarningEvidence.id == warnind_id, WarningEvidence.guild_id == guild_id)).all()