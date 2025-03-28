"""This class is for the guild's config data, which is stored in the database. It is used to store and retrieve data from the database."""
import json
import logging
import os

from classes.singleton import Singleton
from database.databaseController import ConfigDbTransactions

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
				serverid = file[:-5]
				with open(f"configs/{file}", "r") as f :
					config = json.load(f)
					for key, value in config.items() :
						if key == "name" :
							continue
						self.add_key(serverid, key, value, overwrite=True)
				os.remove(f"configs/{file}")
				self.load_guild(serverid)
		os.rmdir("configs")

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

	def add_key(self, serverid, key, value: str|bool|int, overwrite=False) :
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

	def get_key(self, serverid, key) :
		"""Gets a key from the config, throws KeyNotFound if not found"""
		try:
			value: str = self.data[str(serverid)][key.upper()]
			if isinstance(value, bool):
				return value
			if value.isnumeric():
				return int(value)
			return value
		except KeyError:
			raise KeyNotFound(key)

	def get_key_or_none(self, serverid, key) :
		"""Gets a key from the config, returns None if not found"""
		value = self.data[str(serverid)].get(key.upper(), None)
		if value is None :
			return None
		if isinstance(value, bool) :
			return value
		if value.isnumeric() :
			return int(value)
		return value
