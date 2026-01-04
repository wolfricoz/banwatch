from sqlalchemy import Select
from sqlalchemy.util import to_list

from database.current import Staff
from database.transactions.BanReasonTransactions import DatabaseTransactions


class StaffDbTransactions(DatabaseTransactions) :

	def get(self, uid: int) -> Staff | None :
		return session.scalar(Select(Staff).where(Staff.uid == uid))

	def add(self, uid: int, role: str) -> Staff | None :
		if self.get(uid) :
			return None
		new_staff = Staff(uid=uid, role=role.lower())
		session.add(new_staff)
		self.commit(session)
		return new_staff

	def get_all(self) -> list[Staff] :
		return to_list(session.scalars(Select(Staff)).all())

	def delete(self, uid: int) -> bool :
		staff = self.get(uid)
		if not staff :
			return False
		session.delete(staff)
		self.commit(session)
		return True
