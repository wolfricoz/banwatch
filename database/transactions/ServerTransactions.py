import datetime
import logging
from abc import abstractmethod
from datetime import datetime
from typing import Type

from sqlalchemy import ColumnElement, Select, and_, exists, text

from database import current as db
from database.transactions.BanReasonTransactions import DatabaseTransactions
from database.current import Bans, Servers


class ServerDbTransactions(DatabaseTransactions) :

	def exists(self, guild_id: int) -> object :
		"""Check if the server exists in the database.
		@param guild_id:
		@return:
		"""
		return session.query(exists().where(Servers.id == guild_id)).scalar()

	def add(self, guild_id: int, owner: str, name: str, member_count: int, invite: str | None,
	        active: bool = True, owner_id=None) -> Servers | bool :
		"""
		Add a server to the database.
		@param guild_id:
		@param owner:
		@param name:
		@param member_count:
		@param invite:
		@return:
		"""
		logging.info(f"Adding entry to server table with data: {guild_id}, {owner}, {name}, {member_count}, {invite}")
		if self.exists(guild_id) :
			# Call the update function
			self.update(guild_id, owner, name, member_count, invite, delete=False)
			return False
		guild = Servers(id=guild_id, owner=owner, name=name, member_count=member_count, invite=invite, active=active,
		                owner_id=owner_id)
		session.add(guild)
		self.commit(session)
		return guild

	def update(self, guild_id: int, owner: str = None, name: str = None, member_count: int = None, invite: str = None,
	           delete: bool = None, hidden: bool = None, active: bool = None, owner_id: int = None,
	           premium: datetime = None) -> Servers | bool :

		guild = session.scalar(Select(Servers).where(Servers.id == guild_id))
		if not guild :
			return False
		updates = {
			'owner'        : owner,
			'name'         : name,
			'member_count' : member_count,
			'invite'       : invite,
			'deleted_at'   : datetime.now() if delete else None if delete is False else guild.deleted_at,
			'updated_at'   : datetime.now(),
			'hidden'       : hidden,
			'active'       : active,
			'owner_id'     : owner_id,
			'premium'      : premium
		}

		for field, value in updates.items() :
			if field == 'deleted_at' :
				setattr(guild, field, value)
				continue
			if value is not None :
				setattr(guild, field, value)
		self.commit(session)
		logging.info(f"Updated {guild_id} with:")
		logging.info(updates)
		return guild

	def get(self, guild_id: int) -> Type[Servers] | None :
		return session.scalar(Select(Servers).where(Servers.id == guild_id))

	def delete_soft(self, guildid: int) :
		logging.info(f"server soft removed {guildid}.")
		server = self.get(guildid)
		if not server or server.deleted_at :
			return False
		server.deleted_at = datetime.now()
		self.commit(session)
		return True

	def delete_permanent(self, server: int | Type[Servers]) -> bool :
		if isinstance(server, int) :
			server = self.get(server)
		logging.info(f"Permanently removing {server.name}")
		if not server :
			return False
		session.delete(server)
		self.commit(session)
		return True

	def get_bans(self, guild_id: int, uid_only: bool = False) -> list[type[Bans]] | list[int] | list[ColumnElement] :
		if uid_only :
			return [uid[0] for uid in
			        session.query(Bans.uid).filter(and_(Bans.gid == guild_id, Bans.deleted_at.is_(None))).all()]
		return session.query(Bans).join(Servers).filter(
			and_(Bans.gid == guild_id, Bans.hidden == False, Bans.deleted_at.is_(None), Servers.deleted_at.is_(None))).all()

	def get_all(self, id_only: bool = True) :
		if not id_only :
			return session.scalars(Select(Servers).where(Servers.deleted_at.is_(None))).all()
		return [sid[0] for sid in session.query(Servers.id).filter(and_(Servers.deleted_at.is_(None))).all()]

	def get_premium_ids(self) :
		"""
		"""
		return [sid[0] for sid in
		        session.query(Servers.id).filter(and_(Servers.premium.isnot(None), Servers.deleted_at.is_(None))).all()]

	def get_deleted(self) :
		return session.query(Servers).filter(Servers.deleted_at.isnot(None)).all()

	def count(self) :
		return session.execute(text("SELECT count(*) FROM servers")).scalar()

	def is_hidden(self, guild_id: int) :
		return session.scalar(Select(Servers).where(Servers.id == guild_id)).hidden

	@staticmethod
	@abstractmethod
	def get_owners_servers(owner_id) :
		return session.scalars(Select(db.Servers).where(db.Servers.owner_id == owner_id)).all()
