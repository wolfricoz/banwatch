import unittest

from database.transactions.BanTransactions import BanTransactions
from database.transactions.ServerTransactions import ServerTransactions
from database.current import create_bot_database, drop_bot_database, Servers


class TestServerDatabaseOperations(unittest.TestCase) :
	guild_id = 395614061393477632
	user_id = 188647277181665280

	def setUp(self) :
		create_bot_database()
		self.server_controller = ServerTransactions()
		self.ban_controller = BanTransactions()

	def tearDown(self) :
		drop_bot_database()

	def test_add_server_positive_and_negative(self) :
		# Positive: Add a new server
		server_success = self.server_controller.add(self.guild_id, "owner", "server_name", 100, "invite")
		self.assertIsInstance(server_success, Servers)
		self.assertEqual(server_success.id, self.guild_id)

		# Negative: Add a duplicate server (should return False as it updates instead)
		server_failed = self.server_controller.add(self.guild_id, "owner", "server_name", 100, "invite")
		self.assertFalse(server_failed)

	def test_server_exists_positive_and_negative(self) :
		# Positive: Check for an existing server
		self.server_controller.add(self.guild_id, "owner", "server_name", 100, "invite")
		self.assertTrue(self.server_controller.exists(self.guild_id))

		# Negative: Check for a non-existent server
		self.assertFalse(self.server_controller.exists(12345))

	def test_update_server_positive_and_negative(self) :
		# Positive: Update an existing server
		self.server_controller.add(self.guild_id, "owner", "server_name", 100, "invite")
		server = self.server_controller.update(self.guild_id, owner="new_owner", member_count=200)
		self.assertEqual(server.owner, "new_owner")
		self.assertEqual(server.member_count, 200)

		# Negative: Update a non-existent server
		self.assertFalse(self.server_controller.update(12345, owner="new_owner"))

	def test_server_get_positive_and_negative(self) :
		# Positive: Get an existing server
		self.server_controller.add(self.guild_id, "owner", "server_name", 100, "invite")
		server = self.server_controller.get(self.guild_id)
		self.assertIsNotNone(server)

		# Negative: Get a non-existent server
		self.assertIsNone(self.server_controller.get(12345))

	def test_delete_permanent_positive_and_negative(self) :
		# Positive: Permanently delete a server
		self.server_controller.add(self.guild_id, "owner", "server_name", 100, "invite")
		self.assertTrue(self.server_controller.delete_permanent(self.guild_id))
		self.assertIsNone(self.server_controller.get(self.guild_id))

		# Negative: Delete a non-existent server
		self.assertFalse(self.server_controller.delete_permanent(12345))

	def test_soft_delete_server_positive_and_negative(self) :
		# Positive: Soft delete and restore a server
		self.server_controller.add(self.guild_id, "owner", "server_name", 100, "invite")
		self.server_controller.delete_soft(self.guild_id)
		self.assertIsNotNone(self.server_controller.get(self.guild_id).deleted_at)
		self.server_controller.update(self.guild_id, delete=False)
		self.assertIsNone(self.server_controller.get(self.guild_id).deleted_at)

		# Negative: Soft delete a non-existent server
		self.assertFalse(self.server_controller.delete_soft(12345))

	def test_get_bans_positive_and_negative(self) :
		# Positive: Get bans from a server
		self.server_controller.add(self.guild_id, "owner", "server_name", 100, "invite")
		self.ban_controller.add(self.user_id, self.guild_id, "reason", "staff")
		self.ban_controller.add(self.user_id + 1, self.guild_id, "reason", "staff")
		bans = self.server_controller.get_bans(self.guild_id)
		self.assertEqual(len(bans), 2)

		# Negative: Get bans from a server with no bans
		self.server_controller.add(self.guild_id + 1, "owner", "server_name", 100, "invite")
		bans_empty = self.server_controller.get_bans(self.guild_id + 1)
		self.assertEqual(len(bans_empty), 0)

	def test_get_all_servers_positive_and_negative(self) :
		# Positive: Get all active servers
		self.server_controller.add(self.guild_id, "owner", "server_name", 100, "invite")
		self.server_controller.add(self.guild_id + 1, "owner", "server_name", 100, "invite")
		servers = self.server_controller.get_all()
		self.assertEqual(len(servers), 2)

		# Negative: Get all from an empty database
		self.tearDown()
		self.setUp()
		self.assertEqual(len(self.server_controller.get_all()), 0)

	def test_get_deleted_servers_positive_and_negative(self) :
		# Positive: Get soft-deleted servers
		self.server_controller.add(self.guild_id, "owner", "server_name", 100, "invite")
		self.server_controller.delete_soft(self.guild_id)
		deleted_servers = self.server_controller.get_deleted()
		self.assertEqual(len(deleted_servers), 1)

		# Negative: Get deleted when none are deleted
		self.server_controller.add(self.guild_id + 1, "owner", "server_name", 100, "invite")
		self.assertEqual(len(self.server_controller.get_deleted()), 1) # Still 1 from before
		self.server_controller.update(self.guild_id, delete=False)
		self.assertEqual(len(self.server_controller.get_deleted()), 0)

	def test_count_servers_positive_and_negative(self) :
		# Positive: Count servers
		self.server_controller.add(self.guild_id, "owner", "server_name", 100, "invite")
		self.server_controller.add(self.guild_id + 1, "owner", "server_name", 100, "invite")
		self.assertEqual(self.server_controller.count(), 2)

		# Negative: Count on empty DB
		self.tearDown()
		self.setUp()
		self.assertEqual(self.server_controller.count(), 0)

	def test_hidden_server_positive_and_negative(self) :
		# Positive: Hide and unhide a server
		self.server_controller.add(self.guild_id, "owner", "server_name", 100, "invite")
		server = self.server_controller.update(self.guild_id, hidden=True)
		self.assertTrue(server.hidden)
		self.assertTrue(self.server_controller.is_hidden(self.guild_id))
		server = self.server_controller.update(self.guild_id, hidden=False)
		self.assertFalse(server.hidden)
		self.assertFalse(self.server_controller.is_hidden(self.guild_id))
