from typing import Type

from sqlalchemy import Select

from database.current import Appeals
from database.transactions.BanReasonTransactions import DatabaseTransactions


class AppealsDbTransactions(DatabaseTransactions) :
	def get(self, ban_id: int | str) -> Appeals | None :
		if not ban_id :
			return None
		if isinstance(ban_id, str) :
			ban_id = int(ban_id)
		return session.scalar(Select(Appeals).where(Appeals.ban_id == ban_id))

	def exist(self, ban_id: int) -> Appeals | None :
		return session.scalar(Select(Appeals).where(Appeals.ban_id == ban_id))

	def add(self, ban_id: int, message: str, status="pending") -> bool | Type[Appeals] | Appeals :
		if self.exist(ban_id) :
			return False
		appeal = Appeals(ban_id=ban_id, message=message, status=status)
		session.add(appeal)
		self.commit(session)
		return appeal

	def change_status(self, ban_id, status) :
		appeal: Appeals = self.get(ban_id)
		if not appeal :
			return False
		appeal.status = status
		self.commit(session)
		return True
