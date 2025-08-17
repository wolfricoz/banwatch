import unittest

from database.current import AppealMsgs, create_bot_database, drop_bot_database
from database.databaseController import AppealMsgTransactions, AppealsDbTransactions
from database.factories.ban import BanFactory


class TestAppealMessageDatabaseTransactions(unittest.TestCase) :
	guild_id = 395614061393477632
	user_id = 188647277181665280
	appealMsgController = AppealMsgTransactions()

	def setUp(self) :
		create_bot_database()

	def tearDown(self) :
		drop_bot_database()

	def test_create_message(self) :
		ban = BanFactory().create()
		appeal = AppealsDbTransactions().add(ban.ban_id, "Test")
		appealmsg = self.appealMsgController.add("This is a test", self.user_id, self.guild_id, appeal)
		self.assertIsInstance(appealmsg, AppealMsgs)
		self.assertEqual(appealmsg.message, "This is a test")

	def test_get_all_messages_of_appeal(self) :
		ban = BanFactory().create()
		appeal = AppealsDbTransactions().add(ban.ban_id, "Test")
		self.appealMsgController.add("This is a test1", self.user_id, self.guild_id, appeal)
		self.appealMsgController.add("This is a test2", self.guild_id, self.user_id, appeal)
		self.appealMsgController.add("This is a test3", self.user_id, self.guild_id, appeal)
		self.appealMsgController.add("This is a test4", self.guild_id, self.user_id, appeal)
		msgs = self.appealMsgController.get_chat_log(appeal)
		self.assertEqual(len(msgs), 4)
		self.assertNotEqual(len(msgs), 2)
		testString = "This is a test"
		for position, msg in enumerate(msgs) :
			self.assertIsInstance(msg, AppealMsgs)
			self.assertEqual(msg.message, testString + str(position + 1))
