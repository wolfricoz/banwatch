import unittest

import database.databaseController
from database.current import create_bot_database, drop_bot_database
from database.databaseController import session


class TestServerDatabaseOperations(unittest.TestCase) :
	guild_id = 395614061393477632
	user_id = 188647277181665280

	def setUp(self) :
		create_bot_database()

	def tearDown(self) :
		drop_bot_database()

	# Testing the servers table
	def test_add_server(self) :
		guild_id = self.guild_id
		server_controller = database.databaseController.ServerDbTransactions()
		server_success = server_controller.add(guild_id, "owner", "server_name", 100, "invite")
		self.assertEqual(server_success.id, guild_id)
		server_failed = server_controller.add(guild_id, "owner", "server_name", 100, "invite")
		self.assertFalse(server_failed)
		session.rollback()

	def test_server_exists(self):
		server_controller = database.databaseController.ServerDbTransactions()
		server_controller.add(self.guild_id, "owner", "server_name", 100, "invite")
		self.assertTrue(server_controller.exists(self.guild_id))
		session.rollback()

	def test_update_server(self) :
		guild_id = self.guild_id
		server_controller = database.databaseController.ServerDbTransactions()
		server_controller.add(guild_id, "owner", "server_name", 100, "invite")
		server = server_controller.update(guild_id, owner="new_owner", member_count=200, invite="new_invite")
		self.assertEqual(server.owner, "new_owner")
		self.assertEqual(server.member_count, 200)
		self.assertEqual(server.invite, "new_invite")
		self.assertIsNone(server.deleted_at)
		session.rollback()

	def test_server_get(self):
		server_controller = database.databaseController.ServerDbTransactions()
		server_controller.add(self.guild_id, "owner", "server_name", 100, "invite")
		server = server_controller.get(self.guild_id)
		self.assertIsNotNone(server)
		session.rollback()

	def test_remove_server(self) :
		guild_id = self.guild_id
		user_id = self.user_id
		server_controller = database.databaseController.ServerDbTransactions()
		ban_controller = database.databaseController.BanDbTransactions()
		session.rollback()

		# Ensure the guild exists in the servers table
		server = server_controller.add(guild_id, "owner", "server_name", 100, "invite")

		# Now add the ban
		ban = ban_controller.add(user_id, guild_id, "reason", "staff")
		self.assertTrue(server)
		server = server_controller.delete_permanent(guild_id)
		self.assertIsNone(ban_controller.get(ban.ban_id))
		session.rollback()

	def test_soft_delete_server(self) :
		guild_id = self.guild_id
		server_controller = database.databaseController.ServerDbTransactions()
		server_controller.add(guild_id, "owner", "server_name", 100, "invite")
		server_controller.delete_soft(guild_id)
		self.assertIsNotNone(server_controller.get(guild_id).deleted_at)
		server_controller.update(guild_id, delete=False)
		self.assertIsNone(server_controller.get(guild_id).deleted_at)
		session.rollback()

	def test_get_bans(self):
		server_controller = database.databaseController.ServerDbTransactions()
		server_controller.add(self.guild_id, "owner", "server_name", 100, "invite")
		ban_controller = database.databaseController.BanDbTransactions()
		ban_controller.add(self.user_id, self.guild_id, "reason", "staff")
		ban_controller.add(self.user_id + 1, self.guild_id, "reason", "staff")
		ban_controller.add(self.user_id + 2, self.guild_id, "reason", "staff")
		ban_controller.add(self.user_id + 3, self.guild_id, "reason", "staff")
		ban_controller.add(self.user_id + 4, self.guild_id, "reason", "staff")
		ban_controller.add(self.user_id, self.guild_id + 1, "reason", "staff")
		bans = server_controller.get_bans(self.guild_id)
		self.assertEqual(len(bans), 5)
		session.rollback()

	def get_all_servers(self):
		server_controller = database.databaseController.ServerDbTransactions()
		server_controller.add(self.guild_id, "owner", "server_name", 100, "invite")
		server_controller.add(self.guild_id + 1, "owner", "server_name", 100, "invite")
		server_controller.add(self.guild_id + 2, "owner", "server_name", 100, "invite")
		server_controller.add(self.guild_id + 3, "owner", "server_name", 100, "invite")
		server_controller.add(self.guild_id + 4, "owner", "server_name", 100, "invite")
		server_controller.delete_soft(self.guild_id + 4)
		servers = server_controller.get_all()
		self.assertEqual(len(servers), 4)
		session.rollback()

	def test_get_deleted_servers(self):
		server_controller = database.databaseController.ServerDbTransactions()
		server_controller.add(self.guild_id, "owner", "server_name", 100, "invite")
		server_controller.add(self.guild_id + 1, "owner", "server_name", 100, "invite")
		server_controller.add(self.guild_id + 2, "owner", "server_name", 100, "invite")
		server_controller.add(self.guild_id + 3, "owner", "server_name", 100, "invite")
		server_controller.add(self.guild_id + 4, "owner", "server_name", 100, "invite")
		server_controller.delete_soft(self.guild_id + 4)
		servers = server_controller.get_deleted()
		self.assertEqual(len(servers), 1)
		session.rollback()


	def test_count_servers(self):
		server_controller = database.databaseController.ServerDbTransactions()
		server_controller.add(self.guild_id, "owner", "server_name", 100, "invite")
		server_controller.add(self.guild_id + 1, "owner", "server_name", 100, "invite")
		self.assertEqual(server_controller.count(), 2)

	def test_hidden_server(self):
		server_controller = database.databaseController.ServerDbTransactions()
		server_controller.add(self.guild_id, "owner", "server_name", 100, "invite")
		server = server_controller.update(self.guild_id, hidden=True)
		self.assertTrue(server.hidden)
		server = server_controller.update(self.guild_id, hidden=False)
		self.assertFalse(server.hidden)
		session.rollback()