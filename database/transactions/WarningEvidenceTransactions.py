from typing import List

import discord
from discord.ui import Select
from discord_py_utilities.messages import send_message
from sqlalchemy import select
from sqlalchemy.orm import Mapped

from classes.configdata import ConfigData
from data.config.mappings import Channels
from database.current import WarningEvidence, Warnings
from database.transactions.DatabaseController import DatabaseTransactions



class WarningEvidenceTransactions(DatabaseTransactions) :


	def add(self, warning_id: int | Mapped[int], user_id: int | Mapped[int] , guild_id: int | Mapped[int], message_id: int) -> None:
		with self.createsession() as session:
			entry = WarningEvidence(warning_id=warning_id, user_id=user_id, guild_id=guild_id, message_id=message_id)
			session.add(entry)
			self.commit(session)

	def get_warning(self, warning_id: int) -> Warning :
		with self.createsession() as session:
			return session.scalars(select(WarningEvidence).where(WarningEvidence.warning_id == warning_id)).all()

