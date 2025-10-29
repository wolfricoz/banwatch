"""This class is for the guild's config data, which is stored in the database. It is used to store and retrieve data from the database."""
import json
import logging
import os

import discord
from discord_py_utilities.messages import send_message

from classes.singleton import Singleton
from database.databaseController import ConfigDbTransactions, ServerDbTransactions


class KeyNotFound(Exception) :
	def __init__(self, key) :
		self.key = key
		super().__init__(f"Key {key} not found in config")


class ConfigData(metaclass=Singleton) :
	"""This class generates the config file, with functions to change and get values from it"""

	configcontroller = ConfigDbTransactions
	data = {}

	async def migrate(self) :
		if os.path.isdir("configs") is False :
			logging.info("Configs directory not found")
			return
		for file in os.listdir("configs") :
			if file.endswith(".json") :
				try :
					serverid = file[:-5]
					if serverid.isnumeric() is False :
						continue
					guild = ServerDbTransactions().get(int(serverid))
					if guild is None :
						ServerDbTransactions().add(int(serverid), "None", "None", 0, "None", False)
						continue
					logging.info(f"Migrating config for {serverid}")
					with open(f"configs/{file}", "r") as f :
						config = json.load(f)
						for key, value in config.items() :
							if key.lower() == "name" :
								continue
							self.add_key(serverid, key, value, overwrite=True)
					os.remove(f"configs/{file}")
					self.load_guild(serverid)
				except Exception as e :
					logging.error(e, exc_info=True)

	# os.rmdir("configs")
	def reload(self) :
		"""Reloads the config data from the database"""
		self.data = {}
		for guild in ServerDbTransactions().get_all() :
			try:
				self.load_guild(guild)
			except Exception as e :
				logging.error(e, exc_info=True)

	def load(self, guilds) :
		self.data = {}
		for guild in guilds :
			self.load_guild(guild.id)

	def load_guild(self, serverid) :
		"""Loads the config for a guild"""
		old_config = self.configcontroller.server_config_get(serverid)
		self.data[str(serverid)] = {}
		bool_keys = [
			"allow_appeals",
		]
		for item in old_config :
			if item.key.lower() in bool_keys :
				self.data[str(serverid)][item.key.upper()] = item.value.lower() == "true"
				continue
			self.data[str(serverid)][item.key.upper()] = item.value

	def add_key(self, serverid, key, value: str | bool | int, overwrite=False) :
		"""Adds a key to the config"""

		self.configcontroller.config_unique_add(serverid, key, value, overwrite=overwrite)
		self.load_guild(serverid)

	def remove_key(self, serverid, key) :
		"""Removes a key from the config"""
		self.configcontroller.config_unique_remove(serverid, key)
		self.load_guild(serverid)

	def update_key(self, serverid, key, value) :
		"""Updates a key in the config"""
		self.configcontroller.config_update(serverid, key, value)
		self.load_guild(serverid)

	def get_key(self, serverid, key, default=None) :
		"""Gets a key from the config, throws KeyNotFound if not found"""

		value: str = self.data.get(str(serverid), {}).get(key.upper(), default)
		if isinstance(value, bool) :
			return value
		if isinstance(str, bool) :
			return value
		if value.isnumeric() :
			return int(value)
		if value is None and default is not None:
			return default

		raise KeyNotFound(key)



	def get_key_or_none(self, serverid, key) :
		"""Gets a key from the config, returns None if not found"""
		value: str = self.data.get(str(serverid), {}).get(key.upper(), None)
		if value is None :
			return None
		if isinstance(value, bool) :
			return value
		if isinstance(str, bool) :
			return value
		if value.isnumeric() :
			return int(value)
		return value

	async def get_channel(self, guild: discord.Guild, channel_type: str = "modchannel") -> discord.TextChannel | None :
		"""Gets the channel from the config"""
		channel_id = self.get_key_or_none(guild.id, channel_type)
		if channel_id is None :
			await send_message(guild.owner,
			                   f"No `{channel_type}` channel set for {guild.name}, please set it up using the /config command")
			return None
		channel = guild.get_channel(channel_id)
		if channel is None :
			await send_message(guild.owner,
			                   f"Cannot find `{channel_type}` channel with id {channel_id} in {guild.name}, please set it up using the /config command")
			return None
		return channel
