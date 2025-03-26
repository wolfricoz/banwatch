import unittest

import database.databaseController
from classes.access import AccessControl
from classes.configdata import ConfigData
from database.current import create_bot_database, drop_bot_database
from database.databaseController import ConfigDbTransactions, StaffDbTransactions, session
from database.factories.serverfactory import ServerFactory


class TestConfigFata(unittest.TestCase) :
	config_controller= ConfigData()

	def setUp(self) :
		create_bot_database()

	def tearDown(self) :
		drop_bot_database()

	# Adding keys to the config
	def test_add_config_string(self):
		guild = ServerFactory().create()
		self.config_controller.add_key(guild.id, "TEST_MESSAGE", "This is a test message")
		self.assertEqual(ConfigDbTransactions.config_unique_get(guild.id, "TEST_MESSAGE"), "This is a test message")

	def test_add_config_int(self):
		guild = ServerFactory().create()
		channel_id = 123456789
		self.config_controller.add_key(guild.id, "MODCHANNEL", channel_id)
		self.assertEqual(int(ConfigDbTransactions.config_unique_get(guild.id, "MODCHANNEL")), channel_id)

	def test_add_config_bool(self):
		guild = ServerFactory().create()
		self.config_controller.add_key(guild.id, "ALLOW_APPEALS", True)
		self.assertEqual(ConfigDbTransactions.config_unique_get(guild.id, "ALLOW_APPEALS") == "True", True)
		self.config_controller.add_key(guild.id, "ALLOW_APPEALS", False, overwrite=True)
		self.assertEqual(ConfigDbTransactions.config_unique_get(guild.id, "ALLOW_APPEALS") == "True", False)

	def test_add_config_override(self):
		guild = ServerFactory().create()
		self.config_controller.add_key(guild.id, "TEST_MESSAGE", "This is a test message")
		self.config_controller.add_key(guild.id, "TEST_MESSAGE", "This is a new test message", overwrite=True)
		self.assertEqual(ConfigDbTransactions.config_unique_get(guild.id, "TEST_MESSAGE"), "This is a new test message")

	# Getting keys from the config
	def test_get_str(self):
		guild = ServerFactory().create()
		self.config_controller.add_key(guild.id, "TEST_MESSAGE", "This is a test message")
		self.assertEqual(self.config_controller.get_key(guild.id, "TEST_MESSAGE"), "This is a test message")
		self.assertEqual(self.config_controller.get_key_or_none(guild.id, "TEST_MESSAGE"), "This is a test message")

	def test_get_int(self):
		guild = ServerFactory().create()
		channel_id = 123456789
		self.config_controller.add_key(guild.id, "MODCHANNEL", channel_id)
		self.assertEqual(self.config_controller.get_key(guild.id, "MODCHANNEL"), channel_id)
		self.assertEqual(self.config_controller.get_key_or_none(guild.id, "MODCHANNEL"), channel_id)

	def test_get_bool(self):
		guild = ServerFactory().create()
		self.config_controller.add_key(guild.id, "ALLOW_APPEALS", True)
		self.assertEqual(self.config_controller.get_key(guild.id, "ALLOW_APPEALS"), True)
		self.assertEqual(self.config_controller.get_key_or_none(guild.id, "ALLOW_APPEALS"), True)
		self.config_controller.add_key(guild.id, "ALLOW_APPEALS", False, overwrite=True)
		self.assertEqual(self.config_controller.get_key(guild.id, "ALLOW_APPEALS"), False)
		self.assertEqual(self.config_controller.get_key_or_none(guild.id, "ALLOW_APPEALS"), False)

	def test_update(self):
		guild = ServerFactory().create()
		self.config_controller.add_key(guild.id, "ALLOW_APPEALS", True)
		self.assertEqual(self.config_controller.get_key(guild.id, "ALLOW_APPEALS"), True)
		self.config_controller.update_key(guild.id, "ALLOW_APPEALS", False)
		self.assertEqual(self.config_controller.get_key(guild.id, "ALLOW_APPEALS"), False)

	def test_delete(self):
		guild = ServerFactory().create()
		self.config_controller.add_key(guild.id, "ALLOW_APPEALS", True)
		self.assertEqual(self.config_controller.get_key(guild.id, "ALLOW_APPEALS"), True)
		self.config_controller.remove_key(guild.id, "ALLOW_APPEALS")
		self.assertEqual(self.config_controller.get_key_or_none(guild.id, "ALLOW_APPEALS"), None)



