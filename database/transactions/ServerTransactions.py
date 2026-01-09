import datetime
import logging
from datetime import datetime
from typing import Type

from sqlalchemy import ColumnElement, Select, and_, exists, text

from database import current as db
from database.current import Bans, Servers
from database.transactions.DatabaseController import DatabaseTransactions


class ServerTransactions(DatabaseTransactions) :


	def exists(self, guild_id: int) -> object :
		"""Check if the server exists in the database.
		@param guild_id:
		@return:
		"""
		with self.createsession() as session :

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
		with self.createsession() as session :

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
		with self.createsession() as session :


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

	def get(self, guild_id: int, current_session = None) -> Type[Servers] | None :
		if current_session :
			return current_session.scalar(Select(Servers).where(Servers.id == guild_id))
		with self.createsession() as session :

			return session.scalar(Select(Servers).where(Servers.id == guild_id))

	def delete_soft(self, guildid: int) :
		with self.createsession() as session :

			logging.info(f"server soft removed {guildid}.")
			server = self.get(guildid, session)
			if not server or server.deleted_at :
				return False
			server.deleted_at = datetime.now()
			self.commit(session)
			return True

	def delete_permanent(self, server: int | Type[Servers]) -> bool :
		with self.createsession() as session :

			if isinstance(server, int) :
				server = self.get(server)
			if not server :
				logging.info(f"{self} not found for permanent deletion.")
				return False
			logging.info(f"Permanently removing {server.name}")

			session.delete(server)
			self.commit(session)
			return True

	def get_bans(self, guild_id: int, uid_only: bool = False) -> list[type[Bans]] | list[int] | list[ColumnElement] :
		with self.createsession() as session :

			if uid_only :
				return [uid[0] for uid in
				        session.query(Bans.uid).filter(and_(Bans.gid == guild_id, Bans.deleted_at.is_(None))).all()]
			return session.query(Bans).join(Servers).filter(
				and_(Bans.gid == guild_id, Bans.hidden == False, Bans.deleted_at.is_(None), Servers.deleted_at.is_(None))).all()

	def get_all(self, id_only: bool = True) :
		with self.createsession() as session :

			if not id_only :
				return session.scalars(Select(Servers).where(Servers.deleted_at.is_(None))).all()
			return [sid[0] for sid in session.query(Servers.id).filter(and_(Servers.deleted_at.is_(None))).all()]

	def get_premium_ids(self) :
		"""
		"""
		with self.createsession() as session :

			return [sid[0] for sid in
			        session.query(Servers.id).filter(and_(Servers.premium.isnot(None), Servers.deleted_at.is_(None))).all()]

	def get_deleted(self) :
		with self.createsession() as session :

			return session.query(Servers).filter(Servers.deleted_at.isnot(None)).all()

	def count(self) :
		with self.createsession() as session :

			return session.execute(text("SELECT count(*) FROM servers")).scalar()

	def is_hidden(self, guild_id: int) :
		with self.createsession() as session :

			return session.scalar(Select(Servers).where(Servers.id == guild_id)).hidden


	def get_owners_servers(self, owner_id) :
		with self.createsession() as session :

			return session.scalars(Select(db.Servers).where(db.Servers.owner_id == owner_id)).all()
