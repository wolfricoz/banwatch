import logging
from abc import abstractmethod

from sqlalchemy import Select

from database.current import *
from database.transactions.DatabaseController import DatabaseTransactions


class BanReasonsTransactions(DatabaseTransactions) :

	def get(self, name: str) -> BanReasons | None :
		with self.createsession() as session :

			return session.scalar(Select(BanReasons).where(BanReasons.name == name))


	def exists(self, reason: str) -> bool :
		with self.createsession() as session :

			return session.scalar(Select(BanReasons).where(BanReasons.reason == reason)) is not None


	def get_by_server(self, server_id: int, active_only: bool = False) -> list[BanReasons] :
		with self.createsession() as session :

			stmt = Select(BanReasons).where(BanReasons.server_id == server_id)
			if active_only :
				stmt = stmt.where(BanReasons.active.is_(True))
			return session.scalars(stmt).all()


	def get_all(self, active_only: bool = False) -> list[BanReasons] :
		with self.createsession() as session :

			stmt = Select(BanReasons)
			if active_only :
				stmt = stmt.where(BanReasons.active.is_(True))
			return session.scalars(stmt).all()


	def add(self, server_id: int, name: str, description: str, reason: str, active: bool = True) -> BanReasons | bool :
		with self.createsession() as session :

			if BanReasonsTransactions().exists(reason) :
				logging.warning(f"Attempt to add existing ban reason: {reason}")
				return False
			entry = BanReasons(server_id=server_id, name=name, description=description, reason=reason, active=active)
			session.add(entry)
			DatabaseTransactions().commit(session)
			return entry

	def update(self, reason_id: int | BanReasons, name: str = None, description: str = None, reason: str = None,
	           active: bool = None) -> BanReasons | bool :
		with self.createsession() as session :

			if isinstance(reason_id, int) :
				entry = BanReasonsTransactions().get(reason_id)
			else :
				entry = reason_id
			if not entry :
				return False
			updates = {
				"name"        : name,
				"description" : description,
				"reason"      : reason,
				"active"      : active
			}
			for field, value in updates.items() :
				if value is not None :
					setattr(entry, field, value)
			DatabaseTransactions().commit(session)
			return entry


	def delete(self, reason_id: int | BanReasons) -> bool :
		with self.createsession() as session :

			if isinstance(reason_id, int) :
				entry = BanReasonsTransactions().get(reason_id)
			else :
				entry = reason_id
			if not entry :
				return False
			session.delete(entry)
			DatabaseTransactions().commit(session)
			return True

	def toggle_active(self, reason_id: int | BanReasons, value: bool) -> bool :
		with self.createsession() as session :

			if isinstance(reason_id, int) :
				entry = BanReasonsTransactions().get(reason_id)
			else :
				entry = reason_id
			if not entry :
				return False
			entry.active = value
			DatabaseTransactions().commit(session)
			return True
