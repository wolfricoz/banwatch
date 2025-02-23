import unittest

import database.databaseController
from database.current import create_bot_database, drop_bot_database
from database.databaseController import session


class TestDatabaseOperations(unittest.TestCase) :
	guild_id = 395614061393477632
	user_id = 188647277181665280

	def setUp(self) :
		create_bot_database()

	def tearDown(self) :
		drop_bot_database()

	# Testing the bans table
	def test_add_ban(self) :
		guild_id = self.guild_id
		user_id = self.user_id
		server_controller = database.databaseController.ServerDbTransactions()
		ban_controller = database.databaseController.BanDbTransactions()

		# Ensure the guild exists in the servers table
		server_controller.add(guild_id, "owner", "server_name", 100, "invite")

		# Now add the ban
		ban = ban_controller.add(user_id, guild_id, "reason", "staff")
		self.assertEqual(ban.ban_id, user_id + guild_id)
		ban = ban_controller.add(user_id, guild_id, "reason", "staff")
		self.assertFalse(ban)
		session.rollback()

	def test_get_ban(self) :
		guild_id = self.guild_id
		user_id = self.user_id
		server_controller = database.databaseController.ServerDbTransactions()
		ban_controller = database.databaseController.BanDbTransactions()
		ban_id = guild_id + user_id
		# Ensure the guild exists in the servers table
		server_controller.add(guild_id, "owner", "server_name", 100, "invite")

		# Now add the ban
		ban = ban_controller.add(user_id, guild_id, "reason", "staff", approved=True)
		assert_entry = ban_controller.get(ban_id)
		self.assertIsNotNone(assert_entry)
		self.assertEqual(assert_entry.ban_id, user_id + guild_id)
		session.rollback()

	def test_delete_ban(self) :
		guild_id = self.guild_id
		user_id = self.user_id
		server_controller = database.databaseController.ServerDbTransactions()
		ban_controller = database.databaseController.BanDbTransactions()

		# Ensure the guild exists in the servers table
		server_controller.add(guild_id, "owner", "server_name", 100, "invite")

		# Now add the ban
		ban = ban_controller.add(user_id, guild_id, "reason", "staff")
		self.assertTrue(ban_controller.delete_soft(ban.ban_id))
		self.assertIsNone(ban_controller.get(ban.ban_id))
		session.rollback()

	def test_get_guild_status_from_ban(self) :
		guild_id = self.guild_id
		user_id = self.user_id
		server_controller = database.databaseController.ServerDbTransactions()
		ban_controller = database.databaseController.BanDbTransactions()
		ban_id = guild_id + user_id
		# Ensure the guild exists in the servers table
		guild = server_controller.add(guild_id, "owner", "server_name", 100, "invite")

		# Now add the ban
		ban_controller.add(user_id, guild_id, "reason", "staff")
		ban = ban_controller.get(ban_id)

		self.assertEqual(ban.guild.deleted_at, None)
		server_controller.update(guild.id, delete=True)
		self.assertIsNone(ban_controller.get(ban.ban_id))

	def test_update_ban(self) :
		guild_id = self.guild_id
		user_id = self.user_id
		server_controller = database.databaseController.ServerDbTransactions()
		ban_controller = database.databaseController.BanDbTransactions()

		# Ensure the guild exists in the servers table
		server_controller.add(guild_id, "owner", "server_name", 100, "invite")

		# Now add the ban
		ban = ban_controller.add(user_id, guild_id, "reason", "staff")
		self.assertFalse(ban.verified)
		self.assertFalse(ban.hidden)
		ban = ban_controller.update(ban.ban_id, verified=True, hidden=True)
		self.assertTrue(ban.verified)
		self.assertTrue(ban.hidden)

		session.rollback()

	# proof table
	#
	def test_add_proof(self) :
		guild_id = self.guild_id
		user_id = self.user_id
		server_controller = database.databaseController.ServerDbTransactions()
		ban_controller = database.databaseController.BanDbTransactions()
		proof_controller = database.databaseController.ProofDbTransactions()

		# Ensure the guild exists in the servers table
		server_controller.add(guild_id, "owner", "server_name", 100, "invite")

		# Now add the ban
		ban = ban_controller.add(user_id, guild_id, "reason", "staff")
		proof = proof_controller.add(ban.ban_id, self.user_id, "proof", [
			"https://cdn.discordapp.com/attachments/1295854818589413467/1295857322576445593/23378040040df75049c1c8c0819b809e.png?ex=67102cad&is=670edb2d&hm=b78477e9b44e99243b927d206d7bb75a3a3c8a97f42a0e891f055586f1a0b97d&",
			"https://cdn.discordapp.com/attachments/1295854818589413467/1295857330360946718/9e3da3ba884c1330c0d326ce19678a09.png?ex=67102caf&is=670edb2f&hm=e5bd9aadb63f202c8e509da2962dad66454ef7b88816074871d8df1b192d4593&"])
		self.assertEqual(proof.ban_id, ban.ban_id)
		self.assertEqual(proof.proof, "proof")
		self.assertEqual(proof.get_attachments(), [
			"https://cdn.discordapp.com/attachments/1295854818589413467/1295857322576445593/23378040040df75049c1c8c0819b809e.png?ex=67102cad&is=670edb2d&hm=b78477e9b44e99243b927d206d7bb75a3a3c8a97f42a0e891f055586f1a0b97d&",
			"https://cdn.discordapp.com/attachments/1295854818589413467/1295857330360946718/9e3da3ba884c1330c0d326ce19678a09.png?ex=67102caf&is=670edb2f&hm=e5bd9aadb63f202c8e509da2962dad66454ef7b88816074871d8df1b192d4593&"])
