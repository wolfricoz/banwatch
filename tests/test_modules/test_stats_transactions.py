import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import Select

from database.current import Appeals, Bans, Servers, create_bot_database, drop_bot_database
from database.transactions.AppealsTransactions import AppealsDbTransactions
from database.transactions.BanTransactions import BanTransactions
from database.transactions.ProofTransactions import ProofTransactions
from database.transactions.ServerTransactions import ServerTransactions
from database.transactions.StatsTransactions import StatsTransactions


class TestStatsTransactions(unittest.TestCase) :
	guild_id = 395614061393477632

	def setUp(self) :
		create_bot_database()
		self.stats = StatsTransactions()
		self.now = datetime.now(tz=timezone.utc)
		self.start = self.now - timedelta(days=7)
		ServerTransactions().add(self.guild_id, "owner", "Test server", 100, "")

	# ============================================================
	def tearDown(self) :
		drop_bot_database()

	# ============================================================
	def _ban(self, uid: int, created: datetime, **values) -> int :
		ban = BanTransactions().add(uid, self.guild_id, "reason", "staff",
		                            approved=values.pop("approved", False), hidden=values.pop("hidden", False))
		with self.stats.createsession() as session :
			row = session.scalar(Select(Bans).where(Bans.ban_id == ban.ban_id))
			row.created_at = created
			for key, value in values.items() :
				setattr(row, key, value)
			self.stats.commit(session)
		return ban.ban_id

	# ============================================================
	def test_bans_split_by_window(self) :
		with_proof = self._ban(1, self.now - timedelta(days=1))
		ProofTransactions().add(with_proof, 1, "proof", [])
		self._ban(2, self.now - timedelta(days=2), hidden=True)
		self._ban(3, self.now - timedelta(days=10), deleted_at=self.now - timedelta(days=1))

		this_week = self.stats.bans(self.start, self.now)
		last_week = self.stats.bans(self.start - timedelta(days=7), self.start)

		self.assertEqual(this_week, {"new" : 2, "hidden" : 1, "verified" : 0, "with_proof" : 1, "removed" : 1})
		self.assertEqual(last_week["new"], 1)

	# ============================================================
	def test_review_queue(self) :
		self._ban(1, self.now - timedelta(days=3))
		self._ban(2, self.now - timedelta(days=1))
		self._ban(3, self.now - timedelta(days=5), approved=True)

		queue = self.stats.review_queue(self.now)

		self.assertEqual(queue["waiting"], 2)
		self.assertAlmostEqual(queue["oldest_age"].total_seconds(), 3 * 86400, delta=5)

	# ============================================================
	def test_top_servers(self) :
		self._ban(1, self.now - timedelta(days=1))
		self._ban(2, self.now - timedelta(days=1))

		self.assertEqual(self.stats.top_servers(self.start, self.now), [("Test server", 2)])

	# ============================================================
	def test_appeals(self) :
		for uid, status in ((1, "pending"), (2, "approved"), (3, "denied")) :
			ban_id = self._ban(uid, self.now - timedelta(days=2))
			AppealsDbTransactions().add(ban_id, "please", status=status)
		with self.stats.createsession() as session :
			for appeal in session.scalars(Select(Appeals)).all() :
				appeal.created_at = self.now - timedelta(days=2)
				appeal.updated_at = self.now - timedelta(days=1)
			self.stats.commit(session)

		appeals = self.stats.appeals(self.start, self.now, self.now)

		self.assertEqual(appeals["new"], 3)
		self.assertEqual(appeals["approved"], 1)
		self.assertEqual(appeals["denied"], 1)
		self.assertEqual(appeals["pending"], 1)
		self.assertAlmostEqual(appeals["oldest_age"].total_seconds(), 2 * 86400, delta=5)

	# ============================================================
	def test_servers(self) :
		with self.stats.createsession() as session :
			server = session.scalar(Select(Servers).where(Servers.id == self.guild_id))
			server.created_at = self.now - timedelta(days=1)
			server.premium = self.now + timedelta(days=3)
			self.stats.commit(session)

		servers = self.stats.servers(self.start, self.now, self.now)

		self.assertEqual(servers, {"new" : 1, "active" : 1, "members" : 100, "hidden" : 0, "premium_expiring" : 1})

	# ============================================================
	def test_bans_from_server(self) :
		joined = self.now - timedelta(days=2)
		self._ban(1, self.now - timedelta(days=1))
		self._ban(2, self.now - timedelta(days=1), hidden=True)
		self._ban(3, self.now - timedelta(days=5))

		self.assertEqual(self.stats.bans_from_server(self.guild_id, joined), {"added" : 2, "shared" : 1})

	# ============================================================
	def test_empty_database(self) :
		self.assertEqual(self.stats.review_queue(self.now), {"waiting" : 0, "oldest_age" : None})
		self.assertEqual(self.stats.warnings(self.start, self.now), {"new" : 0, "evidence" : 0})
