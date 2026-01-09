import datetime
import logging
from datetime import datetime
from typing import Type

from sqlalchemy import Select, and_, text
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.strategies import JoinedLoader

from classes.singleton import Singleton
from database.current import Bans, Proof, Servers
from database.transactions.DatabaseController import DatabaseTransactions
from database.transactions.ServerTransactions import ServerTransactions


class BanTransactions(DatabaseTransactions, metaclass=Singleton) :
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
		with self.createsession() as session :

			ban = session.scalar(Select(Bans).where(Bans.ban_id == ban_id))
			if ban is not None and ban.deleted_at and remove_deleted :
				self.delete_permanent(ban_id)
				return False
			return session.scalar(Select(Bans).where(Bans.ban_id == ban_id))

	def add(self, uid: int, gid: int, reason: str, staff: str, approved: bool = False, verified: bool = False,
	        hidden: bool = False, remove_deleted: bool = False) -> Bans | bool :
		with self.createsession() as session :

			logging.info(f"Adding ban {uid} in {gid} with reason {reason} by {staff}")
			if ServerTransactions().exists(gid) is False :
				return False
			if self.exists(uid + gid, remove_deleted=remove_deleted) :
				return False
			ban = Bans(ban_id=uid + gid, uid=uid, gid=gid, reason=reason, approved=approved, verified=verified, hidden=hidden,
			           staff=staff, deleted_at=None)
			session.add(ban)
			self.commit(session)
			return ban

	def get(self, ban_id: int = None, current_session = None, override: bool = False) -> Type[Bans] | None :
		with self.createsession() as session :
			if current_session :
				session = current_session
			if override :
				return session.scalar(Select(Bans).options(joinedload(Bans.guild)).where(Bans.ban_id == ban_id))
			return session.query(Bans) \
				.options(joinedload(Bans.guild)) \
				.join(Proof, Proof.ban_id == Bans.ban_id, isouter=True) \
				.join(Servers, Servers.id == Bans.gid) \
				.filter(
				Bans.ban_id == ban_id,
				Bans.deleted_at.is_(None),
				Bans.hidden.is_(False),
				Servers.deleted_at.is_(None),
				Servers.hidden.is_(False)
			).first()

	def get_all_user(self, user_id, override=False) :
		with self.createsession() as session :

			if override :
				return session.scalars(Select(Bans).where(Bans.uid == user_id)).all()
			return session.query(Bans).options(joinedload(Bans.guild)).join(Servers).filter(
				and_(Bans.uid == user_id, Bans.deleted_at.is_(None), Bans.hidden.is_(False), Servers.deleted_at.is_(None),
				     Bans.approved.is_(True), Servers.hidden.is_(False))).all()

	def count_all_user(self, user_id, override=False) :
		with self.createsession() as session :

			if override :
				return session.query(Bans).where(Bans.uid == user_id).count()
			return session.query(Bans).join(Servers).filter(
				and_(Bans.uid == user_id, Bans.deleted_at.is_(None), Bans.hidden.is_(False), Servers.deleted_at.is_(None),
				     Bans.approved.is_(True), Servers.hidden.is_(False))).count()

	def get_all(self, override=False) :
		with self.createsession() as session :

			if override :
				return session.scalars(Select(Bans).options(joinedload(Bans.guild))).all()
			return session.scalars(
				Select(Bans).options(joinedload(Bans.guild)).where(
					and_(Bans.deleted_at.is_(None), Bans.hidden.is_(False), Bans.approved.is_(True), Servers.deleted_at.is_(None),
					     Servers.hidden.is_(False)))).all()

	def get_all_pending(self) :
		with self.createsession() as session :

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
		with self.createsession() as session :

			match result_type.lower() :
				case "available" :
					return session.execute(text("SELECT count(*) FROM bans WHERE hidden = false AND deleted_at IS NULL")).scalar()
				case "verified" :
					return session.execute(text("SELECT count(*) FROM bans WHERE verified = true")).scalar()
				case "hidden" :
					return session.execute(text("SELECT count(*) FROM bans WHERE hidden = true")).scalar()
				case "deleted" :
					return session.execute(text("SELECT count(*) FROM bans WHERE deleted_at IS NOT NULL")).scalar()
				case _ :
					return session.execute(text("SELECT count(*) FROM bans")).scalar()

	def delete_soft(self, ban_id: int) -> bool :
		with self.createsession() as session :

			logging.info(f"Ban soft removed {ban_id}.")
			ban = self.get(ban_id, session)
			if not ban or ban.deleted_at :
				return False
			ban.deleted_at = datetime.now()
			self.commit(session)
			return True

	def delete_permanent(self, ban: int | Type[Bans]) -> bool :
		with self.createsession() as session :

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
	           created_at: datetime = None,
	           deleted_at: bool = None,
	           message: int = None
	           ) -> bool | Bans | type[Bans] :
		with self.createsession() as session :

			if isinstance(ban, int) :
				ban = self.get(ban, session, override=True)
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
		with self.createsession() as session :
			return session.query(Bans).filter(Bans.deleted_at.isnot(None)).all()
