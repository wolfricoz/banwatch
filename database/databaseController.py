import datetime
import logging
from abc import ABC, abstractmethod
from typing import Type

import sqlalchemy
from sqlalchemy import ColumnElement, Select, and_, exists, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.util import to_list

import database.current as db
from classes.singleton import Singleton
from database.current import *
from database.current import Servers

session = Session(bind=db.engine, expire_on_commit=False)


class ConfigNotFound(Exception) :
	"""config item was not found or has not been added yet."""

	def __init__(self, message="guild config has not been loaded yet or has not been created yet.") :
		self.message = message
		super().__init__(self.message)


class CommitError(Exception) :
	"""the commit failed."""

	def __init__(self, message="Commiting the data to the database failed and has been rolled back; please try again.") :
		self.message = message
		super().__init__(self.message)


class KeyNotFound(Exception) :
	"""config item was not found or has not been added yet."""

	def __init__(self, key) :
		self.key = key
		self.message = f"`{key}` not found in config, please add it using /config"
		super().__init__(self.message)


class DatabaseTransactions :

	def commit(self, session) :
		try :
			session.commit()
		except SQLAlchemyError as e :
			print(e)
			session.rollback()
			raise CommitError()
		finally :
			session.close()

	def refresh(self) :
		session.expire_all()

	def truncate(self, table: str) :
		if table not in ['proof'] :
			return False

		session.execute(text(f"TRUNCATE TABLE {table}"))
		self.commit(session)

	@staticmethod
	@abstractmethod
	def ping_db() :
		try :
			session.connection()
			if session._is_clean() :
				return "alive"
			session.execute(text("SELECT 1"))
			return "alive"
		except sqlalchemy.exc.PendingRollbackError :
			session.rollback()
			session.close()
			return "error"
		except sqlalchemy.exc.InvalidRequestError :
			return "alive"
		except Exception as e :
			logging.error(f"Database ping failed: {e}", exc_info=True)
			return "error"


class ServerDbTransactions(DatabaseTransactions) :

	def exists(self, guild_id: int) -> object :
		"""Check if the server exists in the database.
		@param guild_id:
		@return:
		"""
		return session.query(exists().where(Servers.id == guild_id)).scalar()

	def add(self, guild_id: int, owner: str, name: str, member_count: int, invite: str | None,
	        active: bool = True) -> Servers | bool :
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
		guild = Servers(id=guild_id, owner=owner, name=name, member_count=member_count, invite=invite, active=active)
		session.add(guild)
		self.commit(session)
		return guild

	def update(self, guild_id: int, owner: str = None, name: str = None, member_count: int = None, invite: str = None,
	           delete: bool = None, hidden: bool = None, active: bool = None) -> Servers | bool :

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
			'active'       : active
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
		logging.info(f"Permanently removing {server}")
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

	def get_all(self) :
		return [sid[0] for sid in session.query(Servers.id).filter(and_(Servers.deleted_at.is_(None))).all()]

	def get_deleted(self) :
		return session.query(Servers).filter(Servers.deleted_at.isnot(None)).all()

	def count(self) :
		return session.execute(text("SELECT count(*) FROM servers")).scalar()

	def is_hidden(self, guild_id: int) :
		return session.scalar(Select(Servers).where(Servers.id == guild_id)).hidden


class BanDbTransactions(DatabaseTransactions, metaclass=Singleton) :
	local_cache = {}

	def populate_cache(self) :
		ban: Bans
		bans = self.get_all()
		self.local_cache = {}
		for ban in bans :
			data = {
				"guild"    : ban.guild.name,
				"reason"   : ban.reason,
				"date"     : ban.created_at.strftime("%m/%d/%Y") if ban.message is not None else 'Pre-Banwatch',
				"verified" : "yes" if ban.verified else 'No'
			}
			if str(ban.uid) not in self.local_cache :
				self.local_cache[str(ban.uid)] = {}
			self.local_cache[str(ban.uid)][str(ban.ban_id)] = data

	def exists(self, ban_id: int, remove_deleted: bool = False) -> bool :
		ban = session.scalar(Select(Bans).where(Bans.ban_id == ban_id))
		if ban is not None and ban.deleted_at and remove_deleted :
			self.delete_permanent(ban_id)
			return False
		return session.scalar(Select(Bans).where(Bans.ban_id == ban_id))

	def add(self, uid: int, gid: int, reason: str, staff: str, approved: bool = False, verified: bool = False,
	        hidden: bool = False, remove_deleted: bool = False) -> Bans | bool :
		logging.info(f"Adding ban {uid} in {gid} with reason {reason} by {staff}")
		if self.exists(uid + gid, remove_deleted=remove_deleted) :
			return False
		ban = Bans(ban_id=uid + gid, uid=uid, gid=gid, reason=reason, approved=approved, verified=verified, hidden=hidden,
		           staff=staff, deleted_at=None)
		session.add(ban)
		self.commit(session)
		return ban

	def get(self, ban_id: int = None, override: bool = False) -> Type[Bans] | None :
		if override :
			return session.scalar(Select(Bans).where(Bans.ban_id == ban_id))
		return session.query(Bans).join(Servers).outerjoin(Proof).filter(
			and_(Bans.ban_id == ban_id, Bans.deleted_at.is_(None), Bans.hidden.is_(False), Servers.deleted_at.is_(None),
			     Servers.hidden.is_(False))).first()

	def get_all_user(self, user_id, override=False) :
		if override :
			return session.scalars(Select(Bans).where(Bans.uid == user_id)).all()
		return session.query(Bans).join(Servers).filter(
			and_(Bans.uid == user_id, Bans.deleted_at.is_(None), Bans.hidden.is_(False), Servers.deleted_at.is_(None),
			     Bans.approved.is_(True), Servers.hidden.is_(False))).all()

	def get_all(self, override=False) :
		if override :
			return session.scalars(Select(Bans).join(Servers)).all()
		return session.scalars(
			Select(Bans).join(Servers).where(
				and_(Bans.deleted_at.is_(None), Bans.hidden.is_(False), Bans.approved.is_(True), Servers.deleted_at.is_(None),
				     Servers.hidden.is_(False)))).all()

	def get_all_pending(self) :
		return session.scalars(
			Select(Bans).join(Servers).where(
				and_(Bans.deleted_at.is_(None), Bans.hidden.is_(False), Servers.deleted_at.is_(None),
				     Servers.hidden.is_(False)))).all()

	def count(self, result_type="all") :
		"""
		This function takes: available, approved, hidden, and deleted as result type, leave empty for all bans
		:param result_type:
		:return:
		"""
		match result_type.lower() :
			case "available" :
				return session.execute(text("SELECT count(*) FROM bans where hidden=0 and deleted_at is NULL")).scalar()
			case "verified" :
				return session.execute(text("SELECT count(*) FROM bans where verified=1")).scalar()
			case "hidden" :
				return session.execute(text("SELECT count(*) FROM bans where hidden=1")).scalar()
			case "deleted" :
				return session.execute(text("SELECT count(*) FROM bans where deleted_at is not NULL")).scalar()
			case _ :
				return session.execute(text("SELECT count(*) FROM bans")).scalar()

	def delete_soft(self, ban_id: int) -> bool :
		logging.info(f"Ban soft removed {ban_id}.")
		ban = self.get(ban_id)
		if not ban or ban.deleted_at :
			return False
		ban.deleted_at = datetime.now()
		self.commit(session)
		return True

	def delete_permanent(self, ban: int | Type[Bans]) -> bool :
		if isinstance(ban, int) :
			ban = self.get(ban, override=True)
		logging.info(f"Permanently removing ban: {ban.ban_id}")
		if not ban :
			return False
		session.delete(ban)
		self.commit(session)
		return True

	def update(self, ban: int | Bans | Type[Bans],
	           approved: bool = None,
	           verified: bool = None,
	           hidden: bool = None,
	           created_at: datetime.date = None,
	           deleted_at: bool = None,
	           message: int = None
	           ) -> Type[Bans] | bool :
		if isinstance(ban, int) :
			ban = self.get(ban, override=True)
		if not ban :
			logging.error(f"Ban {ban} not found.")
			return False
		updates = {
			'approved'   : approved,
			'verified'   : verified,
			'hidden'     : hidden,
			'created_at' : created_at,
			'updated_at' : datetime.now(),
			'deleted_at' : datetime.now() if deleted_at else None if deleted_at is False else ban.deleted_at,
			'message'    : message
		}

		for field, value in updates.items() :
			if value is not None :
				setattr(ban, field, value)
		logging.info(f"Updated {ban.ban_id} with:")
		logging.info(updates)
		self.commit(session)
		return ban

	def get_deleted_bans(self) -> list[type[Bans]] :
		return session.query(Bans).filter(Bans.deleted_at.isnot(None)).all()


class ProofDbTransactions(DatabaseTransactions) :

	def exists(self, ban_id: int) :
		return session.scalar(Select(Proof).where(Proof.ban_id == ban_id))

	def add(self, ban_id: int, user_id: int, proof: str, attachments: list[str]) -> Proof | bool :
		logging.info(f"Adding proof for {ban_id} with {proof} and {len(attachments)} attachments")
		proof = Proof(ban_id=ban_id, uid=user_id, proof=proof, attachments=json.dumps(attachments))
		session.add(proof)
		self.commit(session)
		return proof

	def get(self, ban_id: str | int = None, user_id: int = None) -> list | None :
		if isinstance(ban_id, str) :
			ban_id = int(ban_id)
		if user_id :
			return to_list(session.scalars(Select(Proof).join(Bans).where(Proof.uid == user_id)).all())
		return to_list(session.scalars(Select(Proof).join(Bans).where(Proof.ban_id == ban_id)).all())

	def delete(self, id: int) -> bool :
		entry: Proof = session.scalar(Select(Proof).where(Proof.id == id))
		if entry is None :
			return False
		logging.info(f"Deleting evidence {id} from {entry.ban_id}")
		if not entry :
			return False
		session.delete(entry)
		self.commit(session)
		return True


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


class AppealsDbTransactions(DatabaseTransactions) :
	def get(self, ban_id: int|str) -> Appeals | None :
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


class ConfigDbTransactions(ABC) :

	@staticmethod
	@abstractmethod
	def config_update(guildid: int, key: str, value, overwrite=False) :
		if ConfigDbTransactions.key_exists_check(guildid, key) is False :
			return False
		exists = session.scalar(Select(db.Config).where(db.Config.guild == guildid, db.Config.key == key.upper()))
		exists.value = value
		DatabaseTransactions().commit(session)
		return True

	@staticmethod
	@abstractmethod
	def config_unique_add(guildid: int, key: str, value, overwrite=False) :
		# This function should check if the item already exists, if so it will override it or throw an error.

		value = str(value)
		if ConfigDbTransactions.key_exists_check(guildid, key, overwrite) is True and overwrite is False :
			logging.warning(
				f"Attempted to add unique key with data: {guildid}, {key}, {value}, and overwrite {overwrite}, but one already existed. No changes")
			return False
		if ConfigDbTransactions.key_exists_check(guildid, key, overwrite) is True :
			entries = session.scalars(
				Select(db.Config).where(db.Config.guild == guildid, db.Config.key == key.upper())).all()
			for entry in entries :
				session.delete(entry)
		item = db.Config(guild=guildid, key=key.upper(), value=value)
		session.add(item)
		DatabaseTransactions().commit(session)
		logging.info(f"Adding unique key with data: {guildid}, {key}, {value}, and overwrite {overwrite}")
		return True

	@staticmethod
	@abstractmethod
	def toggle_welcome(guildid: int, key: str, value) :
		# This function should check if the item already exists, if so it will override it or throw an error.
		value = str(value)
		guilddata = session.scalar(Select(Config).where(Config.guild == guildid, Config.key == key.upper()))
		if guilddata is None :
			ConfigDbTransactions.config_unique_add(guildid, key, value, overwrite=True)
			return
		guilddata.value = value
		DatabaseTransactions().commit(session)

		return True

	@staticmethod
	@abstractmethod
	def config_unique_get(guildid: int, key: str) :
		if ConfigDbTransactions.key_exists_check(guildid, key) is False :
			return
		exists = session.scalar(Select(db.Config).where(db.Config.guild == guildid, db.Config.key == key.upper()))
		return exists.value

	@staticmethod
	@abstractmethod
	def config_key_add(guildid: int, key: str, value, overwrite) :
		value = str(value)
		if ConfigDbTransactions.key_multiple_exists_check(guildid, key, value) is True :
			return False
		item = db.Config(guild=guildid, key=key.upper(), value=value)
		session.add(item)
		DatabaseTransactions().commit(session)

		return True

	@staticmethod
	@abstractmethod
	def key_multiple_exists_check(guildid: int, key: str, value) :
		exists = session.scalar(
			Select(db.Config).where(db.Config.guild == guildid, db.Config.key == key, db.Config.value == value))
		session.close()
		if exists is not None :
			return True
		return False

	@staticmethod
	@abstractmethod
	def config_key_remove(guildid: int, key: str, value) :
		if ConfigDbTransactions.key_multiple_exists_check(guildid, key, value) is False :
			return False
		exists = session.scalar(
			Select(db.Config).where(db.Config.guild == guildid, db.Config.key == key, db.Config.value == value))
		session.delete(exists)
		DatabaseTransactions().commit(session)

	@staticmethod
	@abstractmethod
	def config_unique_remove(guild_id: int, key: str) :
		if ConfigDbTransactions.key_exists_check(guild_id, key) is False :
			return False
		exists = session.scalar(
			Select(db.Config).where(db.Config.guild == guild_id, db.Config.key == key))
		session.delete(exists)
		DatabaseTransactions().commit(session)

	@staticmethod
	@abstractmethod
	def key_exists_check(guildid: int, key: str, overwrite=False) :
		exists = session.scalar(
			Select(db.Config).where(db.Config.guild == guildid, db.Config.key == key.upper()))
		if exists is None :
			session.close()
			return False
		if overwrite is False :
			return True
		session.delete(exists)
		DatabaseTransactions().commit(session)
		return True

	@staticmethod
	@abstractmethod
	def toggle_add(guildid, key, value="DISABLED") :
		if ConfigDbTransactions.key_exists_check(guildid, "AUTOKICK") is True :
			return
		welcome = Config(guild=guildid, key="AUTOKICK", value="DISABLED")
		session.merge(welcome)
		logging.info(f"Added toggle '{key}' with value '{value}' in {guildid}")
		DatabaseTransactions().commit(session)

	@staticmethod
	@abstractmethod
	def server_config_get(guildid) :
		return session.scalars(Select(db.Config).where(db.Config.guild == guildid)).all()


class FlaggedTermsTransactions(DatabaseTransactions) :

	@staticmethod
	@abstractmethod
	def add(term: str, action: str, regex: bool = False) :
		"""Adds a term to the database"""
		if FlaggedTermsTransactions.exists(term) :
			logging.warning(f"Term '{term}' already exists.")
			return False
		term = db.FlaggedTerms(term=term.lower(), action=action.lower(), regex=regex)
		session.add(term)
		DatabaseTransactions().commit(session)
		return True

	@staticmethod
	@abstractmethod
	def delete(term: str) :
		"""Deletes a term from the database"""
		term = FlaggedTermsTransactions.exists(term)
		if not term:
			return False
		session.delete(term)
		DatabaseTransactions().commit(session)
		return True

	@staticmethod
	@abstractmethod
	def update(term: str, action: str, regex: bool = False) -> bool :
		"""Updates a term from the database"""
		term = FlaggedTermsTransactions.exists(term)
		if not term:
			return False
		term.action = action
		term.regex = regex
		DatabaseTransactions().commit(session)
		return True

	@staticmethod
	@abstractmethod
	def get(term: str) :
		"""Gets a term from the database"""
		return session.scalar(Select(db.FlaggedTerms).where(db.FlaggedTerms.term == term))

	@staticmethod
	@abstractmethod
	def exists(term: str) -> FlaggedTerms | None :
		"""Checks if a term exists in the database"""
		return session.scalar(Select(db.FlaggedTerms).where(db.FlaggedTerms.term == term))

	@staticmethod
	@abstractmethod
	def get_all(action: str | None = None) :
		"""Gets all term from the database"""
		if action is None:
			return session.query(db.FlaggedTerms).all()
		return session.query(db.FlaggedTerms).where(db.FlaggedTerms.action == action.lower()).all()


class AppealMsgTransactions(DatabaseTransactions):

	@staticmethod
	@abstractmethod
	def add(message: str, sender:int, recipient:int, appeal: int | Mapped[int] | Appeals):
		if isinstance(appeal, Appeals):
			appeal = appeal.id
		msg = AppealMsgs(message=message, sender=sender, recipient=recipient, appeal_id=appeal)
		session.add(msg)
		DatabaseTransactions().commit(session)
		return msg

	@staticmethod
	@abstractmethod
	def get_chat_log(appeal: int | Appeals):
		return session.query(AppealMsgs).where(AppealMsgs.appeal_id == appeal.id).order_by(AppealMsgs.created).all()

