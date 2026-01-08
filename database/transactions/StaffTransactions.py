from sqlalchemy import Select
from sqlalchemy.util import to_list

from database.current import Staff
from database.transactions.DatabaseController import DatabaseTransactions


class StaffTransactions(DatabaseTransactions) :

	def get(self, uid: int) -> Staff | None :
		with self.createsession() as session :

			return session.scalar(Select(Staff).where(Staff.uid == uid))

	def add(self, uid: int, role: str) -> Staff | None :
		with self.createsession() as session :

			if self.get(uid) :
				return None
			new_staff = Staff(uid=uid, role=role.lower())
			session.add(new_staff)
			self.commit(session)
			return new_staff

	def get_all(self) -> list[Staff] :
		with self.createsession() as session :

			return to_list(session.scalars(Select(Staff)).all())

	def delete(self, uid: int) -> bool :
		with self.createsession() as session :

			staff = self.get(uid)
			if not staff :
				return False
			session.delete(staff)
			self.commit(session)
			return True
