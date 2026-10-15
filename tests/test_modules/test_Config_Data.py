import unittest

from classes.configdata import ConfigData
from database.current import create_bot_database, drop_bot_database
from database.factories.serverfactory import ServerFactory
from database.transactions.ConfigTransactions import ConfigTransactions


class TestConfigData(unittest.TestCase) :
	config_controller= ConfigData()

	def setUp(self) :
		create_bot_database()

	# ============================================================
	def tearDown(self) :
		drop_bot_database()

	# ============================================================
	# Adding keys to the Config
	def test_add_config_string(self):
		guild = ServerFactory().create()
		self.config_controller.add_key(guild.id, "TEST_MESSAGE", "This is a test message")
		self.assertEqual(ConfigTransactions().config_unique_get(guild.id, "TEST_MESSAGE"), "This is a test message")

	# ============================================================
	def test_add_config_int(self):
		guild = ServerFactory().create()
		channel_id = 123456789
		self.config_controller.add_key(guild.id, "MODCHANNEL", channel_id)
		self.assertEqual(int(ConfigTransactions().config_unique_get(guild.id, "MODCHANNEL")), channel_id)

	# ============================================================
	def test_add_config_bool(self):
		guild = ServerFactory().create()
		self.config_controller.add_key(guild.id, "ALLOW_APPEALS", True)
		self.assertEqual(ConfigTransactions().config_unique_get(guild.id, "ALLOW_APPEALS") == "True", True)
		self.config_controller.add_key(guild.id, "ALLOW_APPEALS", False, overwrite=True)
		self.assertEqual(ConfigTransactions().config_unique_get(guild.id, "ALLOW_APPEALS") == "True", False)

	# ============================================================
	def test_add_config_override(self):
		guild = ServerFactory().create()
		self.config_controller.add_key(guild.id, "TEST_MESSAGE", "This is a test message")
		self.config_controller.add_key(guild.id, "TEST_MESSAGE", "This is a new test message", overwrite=True)
		self.assertEqual(ConfigTransactions().config_unique_get(guild.id, "TEST_MESSAGE"), "This is a new test message")

	# ============================================================
	# Getting keys from the Config
	def test_get_str(self):
		guild = ServerFactory().create()
		self.config_controller.add_key(guild.id, "TEST_MESSAGE", "This is a test message")
		self.assertEqual(self.config_controller.get_key(guild.id, "TEST_MESSAGE"), "This is a test message")
		self.assertEqual(self.config_controller.get_key_or_none(guild.id, "TEST_MESSAGE"), "This is a test message")

	# ============================================================
	def test_get_int(self):
		guild = ServerFactory().create()
		channel_id = 123456789
		self.config_controller.add_key(guild.id, "MODCHANNEL", channel_id)
		self.assertEqual(self.config_controller.get_key(guild.id, "MODCHANNEL"), channel_id)
		self.assertEqual(self.config_controller.get_key_or_none(guild.id, "MODCHANNEL"), channel_id)

	# ============================================================
	def test_get_bool(self):
		guild = ServerFactory().create()
		self.config_controller.add_key(guild.id, "ALLOW_APPEALS", True)
		self.assertEqual(self.config_controller.get_key(guild.id, "ALLOW_APPEALS"), True)
		self.assertEqual(self.config_controller.get_key_or_none(guild.id, "ALLOW_APPEALS"), True)
		self.config_controller.add_key(guild.id, "ALLOW_APPEALS", False, overwrite=True)

		self.assertEqual(self.config_controller.get_key(guild.id, "ALLOW_APPEALS"), False)
		self.assertEqual(self.config_controller.get_key_or_none(guild.id, "ALLOW_APPEALS"), False)

	# ============================================================
	def test_update(self):
		guild = ServerFactory().create()
		self.config_controller.add_key(guild.id, "ALLOW_APPEALS", True)
		self.assertEqual(self.config_controller.get_key(guild.id, "ALLOW_APPEALS"), True)
		self.config_controller.update_key(guild.id, "ALLOW_APPEALS", False)
		self.assertEqual(self.config_controller.get_key(guild.id, "ALLOW_APPEALS"), False)

	# ============================================================
	def test_delete(self):
		guild = ServerFactory().create()
		self.config_controller.add_key(guild.id, "ALLOW_APPEALS", True)
		self.assertEqual(self.config_controller.get_key(guild.id, "ALLOW_APPEALS"), True)
		self.config_controller.remove_key(guild.id, "ALLOW_APPEALS")
		self.assertEqual(self.config_controller.get_key_or_none(guild.id, "ALLOW_APPEALS"), None)


class TestGetChannelMissing(unittest.IsolatedAsyncioTestCase) :
	"""BANWATCH-DP: an unset channel must never raise, and must not nag on every call."""

	def setUp(self) :
		from classes.permissions_notice import PermissionNotice
		PermissionNotice._last_sent.clear()

	def _guild(self, guild_id) :
		import discord
		from unittest.mock import AsyncMock, MagicMock
		guild = MagicMock()
		guild.id = guild_id
		guild.name = "Test Guild"
		guild.owner = MagicMock(spec=discord.Member)
		guild.owner.name = "owner"
		guild.owner.send = AsyncMock(side_effect=discord.Forbidden(MagicMock(status=403), "Cannot send messages to this user"))
		return guild

	async def test_owner_dms_closed_does_not_raise_and_is_throttled(self) :
		from unittest.mock import patch
		guild = self._guild(9001)
		with patch("classes.configdata.ConfigData.get_key_or_none", return_value=None), \
			patch("classes.configdata.find_first_accessible_text_channel", return_value=None) :
			self.assertIsNone(await ConfigData().get_channel(guild))
			self.assertIsNone(await ConfigData().get_channel(guild))
		self.assertEqual(guild.owner.send.await_count, 1)

	async def test_optional_does_not_notify(self) :
		from unittest.mock import patch
		guild = self._guild(9002)
		with patch("classes.configdata.ConfigData.get_key_or_none", return_value=None), \
			patch("classes.configdata.find_first_accessible_text_channel", return_value=None) :
			self.assertIsNone(await ConfigData().get_channel(guild, optional=True))
		guild.owner.send.assert_not_awaited()
