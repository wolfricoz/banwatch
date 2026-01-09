import unittest

from database.transactions.BanTransactions import BanTransactions
from database.transactions.ProofTransactions import ProofTransactions
from database.current import create_bot_database, drop_bot_database, Proof
from database.factories.ban import BanFactory
from database.factories.evidence import EvidenceFactory


class TestProofDatabaseOperations(unittest.TestCase) :
	guild_id = 395614061393477632
	user_id = 188647277181665280

	def setUp(self) :
		create_bot_database()
		self.ban_controller = BanTransactions()
		self.proof_controller = ProofTransactions()

	def tearDown(self) :
		drop_bot_database()

	def test_add_proof_positive(self) :
		ban = BanFactory().create()
		attachments = ["http://example.com/img1.png", "http://example.com/img2.png"]
		proof = self.proof_controller.add(ban.ban_id, self.user_id, "some proof text", attachments)

		self.assertIsInstance(proof, Proof)
		self.assertEqual(proof.ban_id, ban.ban_id)
		self.assertEqual(proof.proof, "some proof text")
		self.assertEqual(proof.get_attachments(), attachments)

	def test_exists_positive_and_negative(self) :
		evidence = EvidenceFactory().create()
		# Positive: Check that existing proof is found
		self.assertIsNotNone(self.proof_controller.exists(evidence.ban_id))
		# Negative: Check that non-existent proof is not found
		self.assertIsNone(self.proof_controller.exists(0))

	def test_get_proof_positive_and_negative(self) :
		evidence = EvidenceFactory().create()
		# Positive: Get by user_id and ban_id
		self.assertEqual(len(self.proof_controller.get(user_id=evidence.uid)), 1)
		self.assertEqual(len(self.proof_controller.get(ban_id=evidence.ban_id)), 1)

		# Negative: Get for non-existent user_id and ban_id
		self.assertEqual(self.proof_controller.get(user_id=0), [])
		self.assertEqual(self.proof_controller.get(ban_id=0), [])

	def test_delete_proof_positive_and_negative(self) :
		evidence = EvidenceFactory().create()
		# Positive: Deleting an existing proof entry returns True
		self.assertTrue(self.proof_controller.delete(evidence.id))
		# After deletion, it should not be found
		self.assertEqual(self.proof_controller.get(ban_id=evidence.ban_id), [])

		# Negative: Deleting a non-existent proof entry returns False
		self.assertFalse(self.proof_controller.delete(99999))
