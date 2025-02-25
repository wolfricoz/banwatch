import unittest

import database.databaseController
from database.current import create_bot_database, drop_bot_database
from database.databaseController import session
from database.factories.evidence import EvidenceFactory


class TestProofDatabaseOperations(unittest.TestCase) :
	guild_id = 395614061393477632
	user_id = 188647277181665280
	server_controller = database.databaseController.ServerDbTransactions()
	ban_controller = database.databaseController.BanDbTransactions()
	proof_controller = database.databaseController.ProofDbTransactions()

	def setUp(self) :
		create_bot_database()

	def tearDown(self) :
		drop_bot_database()

	def test_add_proof(self) :
		guild_id = self.guild_id
		user_id = self.user_id


		# Ensure the guild exists in the servers table
		self.server_controller.add(guild_id, "owner", "server_name", 100, "invite")

		# Now add the ban
		ban = self.ban_controller.add(user_id, guild_id, "reason", "staff")
		proof = self.proof_controller.add(ban.ban_id, self.user_id, "proof", [
			"https://cdn.discordapp.com/attachments/1295854818589413467/1295857322576445593/23378040040df75049c1c8c0819b809e.png?ex=67102cad&is=670edb2d&hm=b78477e9b44e99243b927d206d7bb75a3a3c8a97f42a0e891f055586f1a0b97d&",
			"https://cdn.discordapp.com/attachments/1295854818589413467/1295857330360946718/9e3da3ba884c1330c0d326ce19678a09.png?ex=67102caf&is=670edb2f&hm=e5bd9aadb63f202c8e509da2962dad66454ef7b88816074871d8df1b192d4593&"])
		self.assertEqual(proof.ban_id, ban.ban_id)
		self.assertEqual(proof.proof, "proof")
		self.assertEqual(proof.get_attachments(), [
			"https://cdn.discordapp.com/attachments/1295854818589413467/1295857322576445593/23378040040df75049c1c8c0819b809e.png?ex=67102cad&is=670edb2d&hm=b78477e9b44e99243b927d206d7bb75a3a3c8a97f42a0e891f055586f1a0b97d&",
			"https://cdn.discordapp.com/attachments/1295854818589413467/1295857330360946718/9e3da3ba884c1330c0d326ce19678a09.png?ex=67102caf&is=670edb2f&hm=e5bd9aadb63f202c8e509da2962dad66454ef7b88816074871d8df1b192d4593&"])

	def test_proof_exists(self) :
		evidence = EvidenceFactory().create()
		self.assertTrue(self.proof_controller.exists(evidence.ban_id))
		self.assertFalse(self.proof_controller.exists(0))

	def test_get_proof(self) :
		evidence = EvidenceFactory().create()
		self.assertEqual(len(self.proof_controller.get(user_id=evidence.uid)), 1)
		self.assertEqual(len(self.proof_controller.get(ban_id=evidence.ban_id)), 1)
		self.assertEqual(self.proof_controller.get(user_id=0), [])
		self.assertEqual(self.proof_controller.get(ban_id=0), [])

	def test_delete_proof(self) :
		evidence = EvidenceFactory().create()
		self.assertIsNotNone(self.proof_controller.get(user_id=evidence.uid))
		self.assertIsNotNone(self.proof_controller.get(ban_id=evidence.ban_id))
		self.proof_controller.delete(evidence.id)
		self.assertEqual(self.proof_controller.get(user_id=evidence.uid), [])
		self.assertEqual(self.proof_controller.get(ban_id=evidence.ban_id), [])