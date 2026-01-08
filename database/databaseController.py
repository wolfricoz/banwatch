import logging
from abc import abstractmethod

from sqlalchemy import Select

from database.transactions.BanReasonTransactions import DatabaseTransactions
from database.current import *


class BanReasonsTransactions(DatabaseTransactions) :
	@staticmethod
	@abstractmethod
	def get(name: str) -> BanReasons | None :
		return session.scalar(Select(BanReasons).where(BanReasons.name == name))

	@staticmethod
	@abstractmethod
	def exists(reason: str) -> bool :
		return session.scalar(Select(BanReasons).where(BanReasons.reason == reason)) is not None

	@staticmethod
	@abstractmethod
	def get_by_server(server_id: int, active_only: bool = False) -> list[BanReasons] :
		stmt = Select(BanReasons).where(BanReasons.server_id == server_id)
		if active_only :
			stmt = stmt.where(BanReasons.active.is_(True))
		return session.scalars(stmt).all()

	@staticmethod
	@abstractmethod
	def get_all(active_only: bool = False) -> list[BanReasons] :
		stmt = Select(BanReasons)
		if active_only :
			stmt = stmt.where(BanReasons.active.is_(True))
		return session.scalars(stmt).all()

	@staticmethod
	@abstractmethod
	def add(server_id: int, name: str, description: str, reason: str, active: bool = True) -> BanReasons | bool :
		if BanReasonsTransactions().exists(reason) :
			logging.warning(f"Attempt to add existing ban reason: {reason}")
			return False
		entry = BanReasons(server_id=server_id, name=name, description=description, reason=reason, active=active)
		session.add(entry)
		DatabaseTransactions().commit(session)
		return entry

	@staticmethod
	@abstractmethod
	def update(reason_id: int | BanReasons, name: str = None, description: str = None, reason: str = None,
	           active: bool = None) -> BanReasons | bool :
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

	@staticmethod
	@abstractmethod
	def delete(reason_id: int | BanReasons) -> bool :
		if isinstance(reason_id, int) :
			entry = BanReasonsTransactions().get(reason_id)
		else :
			entry = reason_id
		if not entry :
			return False
		session.delete(entry)
		DatabaseTransactions().commit(session)
		return True

	@staticmethod
	@abstractmethod
	def toggle_active(reason_id: int | BanReasons, value: bool) -> bool :
		if isinstance(reason_id, int) :
			entry = BanReasonsTransactions().get(reason_id)
		else :
			entry = reason_id
		if not entry :
			return False
		entry.active = value
		DatabaseTransactions().commit(session)
		return True
