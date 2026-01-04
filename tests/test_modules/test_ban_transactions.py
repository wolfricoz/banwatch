import unittest

import database.transactions.BanTransactions
import database.transactions.ServerTransactions
import database.databaseController
from database.current import create_bot_database, drop_bot_database
from database.databaseController import session
from database.transactions.ServerTransactions import ServerDbTransactions
from database.factories.ban import BanFactory
from database.factories.serverfactory import ServerFactory


class TestBanDatabaseOperations(unittest.TestCase) :
	guild_id = 395614061393477632
	user_id = 188647277181665280
	server_controller = database.controllers.ServerTransactions.ServerDbTransactions()
	ban_controller = database.transactions.BanTransactions.BanDbTransactions()

	def setUp(self) :
		create_bot_database()

	def tearDown(self) :
		drop_bot_database()

	# Testing the bans table
	def test_add_ban(self) :
		guild_id = self.guild_id
		user_id = self.user_id

		# Ensure the guild exists in the servers table
		self.server_controller.add(guild_id, "owner", "server_name", 100, "invite")

		# Now add the ban
		ban = self.ban_controller.add(user_id, guild_id, "reason", "staff")
		self.assertEqual(ban.ban_id, user_id + guild_id)
		ban = self.ban_controller.add(user_id, guild_id, "reason", "staff")
		self.assertFalse(ban)
		session.rollback()

	def test_get_ban(self) :
		guild_id = self.guild_id
		user_id = self.user_id
		server_controller = database.controllers.ServerTransactions.ServerDbTransactions()
		ban_controller = database.transactions.BanTransactions.BanDbTransactions()
		ban_id = guild_id + user_id
		# Ensure the guild exists in the servers table
		server_controller.add(guild_id, "owner", "server_name", 100, "invite")

		# Now add the ban
		ban = ban_controller.add(user_id, guild_id, "reason", "staff", approved=True)
		assert_entry = ban_controller.get(ban_id)
		self.assertIsNotNone(assert_entry)
		self.assertEqual(assert_entry.ban_id, user_id + guild_id)
		session.rollback()

	def test_update_ban(self) :
		ban = BanFactory().create(approved=False)
		self.assertFalse(ban.verified)
		self.assertFalse(ban.approved)
		ban = self.ban_controller.update(ban.ban_id, verified=True, approved=True)
		self.assertTrue(ban.verified)
		self.assertTrue(ban.approved)

	def test_get_all_bans(self) :
		bans = BanFactory().create(amount=10)
		self.assertEqual(len(self.ban_controller.get_all()), 10)
		self.ban_controller.update(bans[0].ban_id, hidden=True)
		self.assertEqual(len(self.ban_controller.get_all()), 9)

	def test_get_pending_bans(self) :
		bans = BanFactory().create(amount=10, approved=False)
		self.ban_controller.update(bans[0].ban_id, hidden=True)
		bans = BanFactory().create(amount=10, approved=False)
		self.assertEqual(len(self.ban_controller.get_all_pending()), 19)
		ServerDbTransactions().update(bans[0].gid, hidden=True)
		self.assertEqual(len(self.ban_controller.get_all_pending()), 9)

	def test_get_all_user(self):
		guild1 = ServerFactory().create()
		guild2 = ServerFactory().create()
		self.ban_controller.add(self.user_id, guild1.id, "reason", "staff", approved=True)
		self.ban_controller.add(self.user_id, guild2.id, "reason", "staff", approved=True)
		self.assertEqual(len(self.ban_controller.get_all_user(self.user_id)), 2)
	def test_count_bans(self) :
		bans = BanFactory().create(amount=10)
		self.assertEqual(self.ban_controller.count(), 10)
		self.ban_controller.update(bans[0].ban_id, hidden=True)
		self.ban_controller.delete_soft(bans[1].ban_id)
		self.assertEqual(self.ban_controller.count(result_type="available"), 8)
		self.assertEqual(self.ban_controller.count(result_type="hidden"), 1)
		self.assertEqual(self.ban_controller.count(result_type="deleted"), 1)

	def test_ban_exists(self) :
		ban = BanFactory().create()
		self.assertNotEqual(self.ban_controller.exists(ban.ban_id), False)

	def test_soft_delete_ban(self) :
		ServerFactory().create()
		ban = BanFactory().create()
		self.ban_controller.delete_soft(ban.ban_id)
		self.assertIsNone(self.ban_controller.get(ban.ban_id))

	def test_get_soft_deleted_bans(self) :
		bans = BanFactory().create(amount=10)
		BanFactory().create()
		self.assertEqual(len(self.ban_controller.get_all()), 11)
		for ban in bans :
			self.ban_controller.delete_soft(ban.ban_id)
		self.assertEqual(len(self.ban_controller.get_deleted_bans()), 10)

	def test_delete_ban(self) :
		user_id = self.user_id
		server_controller = database.controllers.ServerTransactions.ServerDbTransactions()
		ban_controller = database.transactions.BanTransactions.BanDbTransactions()

		# Ensure the guild exists in the servers table
		server_controller.add(self.guild_id, "owner", "server_name", 100, "invite")

		# Now add the ban
		ban = ban_controller.add(user_id, self.guild_id, "reason", "staff")
		self.assertTrue(ban_controller.delete_soft(ban.ban_id))
		self.assertIsNone(ban_controller.get(ban.ban_id))
		session.rollback()

	def test_get_guild_status_from_ban(self) :
		guild_id = self.guild_id
		user_id = self.user_id
		server_controller = database.controllers.ServerTransactions.ServerDbTransactions()
		ban_controller = database.transactions.BanTransactions.BanDbTransactions()
		ban_id = guild_id + user_id
		# Ensure the guild exists in the servers table
		guild = server_controller.add(guild_id, "owner", "server_name", 100, "invite")

		# Now add the ban
		ban_controller.add(user_id, guild_id, "reason", "staff")
		ban = ban_controller.get(ban_id)

		self.assertEqual(ban.guild.deleted_at, None)
		server_controller.update(guild.id, delete=True)
		self.assertIsNone(ban_controller.get(ban.ban_id))
		session.rollback()
