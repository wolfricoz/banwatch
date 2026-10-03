"""Read-only queries behind the weekly developer stats report (classes.support.weeklyreport).

Every window method takes a [start, end) pair. The queries only use plain counts so they run the same on the
production Postgres database and the MySQL test database.
"""
from datetime import datetime, timedelta

from sqlalchemy import Select, and_, exists, func

from database.current import AppealMsgs, Appeals, Bans, Proof, Servers, WarningEvidence, Warnings
from database.transactions.DatabaseController import DatabaseTransactions


def _between(column, start: datetime, end: datetime) :
	return and_(column >= start, column < end)


# The review queue, matching BanTransactions.count("pending").
PENDING_REVIEW = and_(Bans.approved.is_(False), Bans.verified.is_(False), Bans.hidden.is_(False),
                      Bans.deleted_at.is_(None))


class StatsTransactions(DatabaseTransactions) :

	# ============================================================
	def bans(self, start: datetime, end: datetime) -> dict :
		"""Bans recorded and removed inside the window."""
		created = _between(Bans.created_at, start, end)
		with self.createsession() as session :
			def count(*where) :
				return session.scalar(Select(func.count(Bans.ban_id)).where(*where)) or 0

			return {
				"new"        : count(created),
				"hidden"     : count(created, Bans.hidden.is_(True)),
				"verified"   : count(created, Bans.verified.is_(True)),
				"with_proof" : count(created, exists().where(Proof.ban_id == Bans.ban_id)),
				"removed"    : count(_between(Bans.deleted_at, start, end)),
			}

	# ============================================================
	def review_queue(self, now: datetime) -> dict :
		"""Bans waiting for staff review right now, and how long the oldest has waited."""
		with self.createsession() as session :
			waiting = session.scalar(Select(func.count(Bans.ban_id)).where(PENDING_REVIEW)) or 0
			oldest = session.scalar(Select(func.min(Bans.created_at)).where(PENDING_REVIEW))
			return {"waiting" : waiting, "oldest_age" : _age(now, oldest)}

	# ============================================================
	def top_servers(self, start: datetime, end: datetime, limit: int = 5) -> list[tuple[str, int]] :
		"""The servers that recorded the most bans in the window, as (name, bans)."""
		with self.createsession() as session :
			rows = session.execute(
				Select(Servers.name, func.count(Bans.ban_id).label("total"))
				.join(Servers, Servers.id == Bans.gid)
				.where(_between(Bans.created_at, start, end))
				.group_by(Servers.id, Servers.name)
				.order_by(func.count(Bans.ban_id).desc())
				.limit(limit)
			).all()
			return [(row.name, row.total) for row in rows]

	# ============================================================
	def appeals(self, start: datetime, end: datetime, now: datetime) -> dict :
		"""Appeals opened and decided in the window, and the ones still waiting now."""
		with self.createsession() as session :
			def count(model, *where) :
				return session.scalar(Select(func.count()).select_from(model).where(*where)) or 0

			pending = Appeals.status == "pending"
			oldest = session.scalar(Select(func.min(Appeals.created_at)).where(pending))
			return {
				"new"        : count(Appeals, _between(Appeals.created_at, start, end)),
				# A decision is the last change to an appeal, so updated_at dates it.
				"approved"   : count(Appeals, Appeals.status == "approved", _between(Appeals.updated_at, start, end)),
				"denied"     : count(Appeals, Appeals.status == "denied", _between(Appeals.updated_at, start, end)),
				"messages"   : count(AppealMsgs, _between(AppealMsgs.created, start, end)),
				"pending"    : count(Appeals, pending),
				"oldest_age" : _age(now, oldest),
			}

	# ============================================================
	def warnings(self, start: datetime, end: datetime) -> dict :
		with self.createsession() as session :
			return {
				"new"      : session.scalar(Select(func.count(Warnings.id))
				                            .where(_between(Warnings.created_at, start, end))) or 0,
				"evidence" : session.scalar(Select(func.count(WarningEvidence.id))
				                            .where(_between(WarningEvidence.created_at, start, end))) or 0,
			}

	# ============================================================
	def servers(self, start: datetime, end: datetime, now: datetime) -> dict :
		live = and_(Servers.active.is_(True), Servers.deleted_at.is_(None))
		with self.createsession() as session :
			def count(*where) :
				return session.scalar(Select(func.count(Servers.id)).where(*where)) or 0

			return {
				# The servers row is kept when the bot leaves, so a rejoin is not counted as new.
				"new"              : count(_between(Servers.created_at, start, end)),
				"active"           : count(live),
				"members"          : int(session.scalar(Select(func.coalesce(func.sum(Servers.member_count), 0))
				                                        .where(live)) or 0),
				"hidden"           : count(live, Servers.hidden.is_(True)),
				"premium_expiring" : count(_between(Servers.premium, now, now + timedelta(days=7))),
			}

	# ============================================================
	def bans_from_server(self, guild_id: int, since: datetime) -> dict :
		"""Bans a server added to the network since `since`, for the join-leaver files."""
		added = and_(Bans.gid == guild_id, Bans.created_at >= since)
		with self.createsession() as session :
			def count(*where) :
				return session.scalar(Select(func.count(Bans.ban_id)).where(added, *where)) or 0

			return {"added" : count(), "shared" : count(Bans.hidden.is_(False), Bans.deleted_at.is_(None))}


def _age(now: datetime, moment: datetime | None) -> timedelta | None :
	if moment is None :
		return None
	# MySQL hands back naive datetimes even for timezone columns.
	if moment.tzinfo is None and now.tzinfo is not None :
		moment = moment.replace(tzinfo=now.tzinfo)
	return now - moment
