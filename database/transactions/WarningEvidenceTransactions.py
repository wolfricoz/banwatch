from sqlalchemy import select
from sqlalchemy.orm import Mapped

from database.current import WarningEvidence
from database.transactions.DatabaseController import DatabaseTransactions


class WarningEvidenceTransactions(DatabaseTransactions) :


	def add(self, warning_id: int | Mapped[int], user_id: int | Mapped[int] , guild_id: int | Mapped[int], message_id: int) -> None:
		with self.createsession() as session:
			entry = WarningEvidence(warning_id=warning_id, user_id=user_id, guild_id=guild_id, message_id=message_id)
			session.add(entry)
			self.commit(session)

	# ============================================================
	def get_warning(self, warning_id: int) -> Warning :
		with self.createsession() as session:
			return session.scalars(select(WarningEvidence).where(WarningEvidence.warning_id == warning_id)).all()

