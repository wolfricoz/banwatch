import unittest

import database.databaseController
from database.current import Appeals, create_bot_database, drop_bot_database
from database.databaseController import session, AppealsDbTransactions
from database.factories.ban import BanFactory


class TestAppealsDatabaseOperations(unittest.TestCase) :
	guild_id = 395614061393477632
	user_id = 188647277181665280

	def setUp(self) :
		create_bot_database()

	def tearDown(self) :
		drop_bot_database()

	def test_add_appeal(self) :
		appeal_controller = AppealsDbTransactions()
		ban = BanFactory().create()

		# Ensure the guild exists in the servers table
		appeal = appeal_controller.add(ban.ban_id, "reason")
		self.assertIsInstance(appeal, Appeals)
		self.assertEqual(appeal.ban_id, ban.ban_id)
		appeal = appeal_controller.add(ban.ban_id, "reason")
		self.assertTrue(appeal)

	def test_change_status(self) :
		appeal_controller = AppealsDbTransactions()
		ban = BanFactory().create()

		# Add an appeal first
		appeal_controller.add(ban.ban_id, "reason")
		result = appeal_controller.change_status(ban.ban_id, "approved")
		self.assertTrue(result)

	def test_change_status_returns_false_if_not_exists(self) :
		appeal_controller = AppealsDbTransactions()
		ban = BanFactory().create()

		result = appeal_controller.change_status(ban.ban_id, "approved")
		self.assertFalse(result)

	def test_exist_returns_appeal_if_exists(self) :
		appeal_controller = AppealsDbTransactions()
		ban = BanFactory().create()

		# Add an appeal first
		appeal_controller.add(ban.ban_id, "reason")
		result = appeal_controller.exist(ban.ban_id)
		self.assertIsInstance(result, Appeals)

	def test_exist_returns_none_if_not_exists(self) :
		appeal_controller = AppealsDbTransactions()
		ban = BanFactory().create()

		result = appeal_controller.exist(ban.ban_id)
		self.assertIsNone(result)

	def test_get_returns_appeal_if_exists(self) :
		appeal_controller = AppealsDbTransactions()
		ban = BanFactory().create()

		# Add an appeal first
		appeal_controller.add(ban.ban_id, "reason")
		result = appeal_controller.get(ban.ban_id)
		self.assertIsInstance(result, Appeals)

	def test_get_returns_none_if_not_exists(self) :
		appeal_controller = AppealsDbTransactions()
		ban = BanFactory().create()

		result = appeal_controller.get(ban.ban_id)
		self.assertIsNone(result)