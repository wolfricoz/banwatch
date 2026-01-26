"""This class is for the guild's Config data, which is stored in the database. It is used to store and retrieve data from the database."""
import json
import logging
import os

import discord
from discord import CategoryChannel, ForumChannel, StageChannel, TextChannel, Thread, VoiceChannel
from discord_py_utilities.messages import send_message
from discord_py_utilities.permissions import find_first_accessible_text_channel

from classes.singleton import Singleton
from database.transactions.ConfigTransactions import ConfigTransactions
from database.transactions.ServerTransactions import ServerTransactions


class KeyNotFound(Exception) :
	def __init__(self, key) :
		self.key = key
		super().__init__(f"Key {key} not found in Config")


class ConfigData(metaclass=Singleton) :
	"""This class generates the Config file, with functions to change and get values from it"""

	configcontroller = ConfigTransactions()
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
					guild = ServerTransactions().get(int(serverid))
					if guild is None :
						ServerTransactions().add(int(serverid), "None", "None", 0, "None", False)
						continue
					logging.info(f"Migrating Config for {serverid}")
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
		"""Reloads the Config data from the database"""
		self.data = {}
		for guild in ServerTransactions().get_all() :
			try:
				self.load_guild(guild)
			except Exception as e :
				logging.error(e, exc_info=True)

	def load(self, guilds) :
		self.data = {}
		for guild in guilds :
			self.load_guild(guild.id)

	def load_guild(self, serverid) :
		"""Loads the Config for a guild"""
		config = self.configcontroller.server_config_get(serverid)
		self.data[str(serverid)] = {}

		for item in config :
			self.data[str(serverid)][item.key.upper()] = item.value

	def add_key(self, serverid, key, value: str | bool | int, overwrite=False) :
		"""Adds a key to the Config"""

		self.configcontroller.config_unique_add(serverid, key, value, overwrite=overwrite)
		self.load_guild(serverid)

	def remove_key(self, serverid, key) :
		"""Removes a key from the Config"""
		self.configcontroller.config_unique_remove(serverid, key)
		self.load_guild(serverid)

	def update_key(self, serverid, key, value) :
		"""Updates a key in the Config"""
		self.configcontroller.config_update(serverid, key, value)
		self.load_guild(serverid)

	def get_key(self, serverid, key, default=None) :
		"""Gets a key from the Config, throws KeyNotFound if not found"""
		guild = self.get_guild(serverid)
		value = guild.get(key.upper(), default)
		if not value:
			return default

		if isinstance(value, bool) :
			return value
		if value.isnumeric() and value not in ["0", "1"] :
			return int(value)
		if isinstance(value, str) :
			if value.lower() in  ["true", "1", "ENABLED"] :
				return True
			if value.lower() in  ["false", "0", "DISABLED"] :
				return False

			return value

		return default



	def get_key_or_none(self, serverid, key) :
		"""Gets a key from the Config, returns None if not found"""
		return self.get_key(serverid, key)

		"""Gets channel from the Config."""

	async def get_channel(self, guild: discord.Guild, channel_type: str = "modchannel") -> None | VoiceChannel | StageChannel | ForumChannel | TextChannel | CategoryChannel | Thread :
		"""Gets the channel from the Config"""
		channel_id = self.get_key_or_none(guild.id, channel_type)
		if not isinstance(channel_id, int) :

			if isinstance(channel_id, str) and channel_id.isnumeric() :
				channel_id = int(channel_id)
			else :
				channel_id = None

		if channel_id is None :
			channel = find_first_accessible_text_channel(guild)
			if channel is None:
				channel = guild.owner
			await send_message(channel,
			                   f"No `{channel_type}` channel set for {guild.name}, please set it up using the /Config command")
			return None
		channel = guild.get_channel(channel_id)
		if channel is None:
			attempts = 0
			while attempts < 3 and channel is None:
				try:
					channel = await guild.fetch_channel(channel_id)
				except discord.NotFound:
					continue
				except discord.HTTPException:
					return None
		if channel is None :
			channel = find_first_accessible_text_channel(guild)
			if channel is None:
				channel = guild.owner

			await send_message(channel,
			                   f"Banwatch could not fetch the `{channel_type}` channel with id {channel_id} in {guild.name}, please verify it exists and is accessible by the bot. If it does then discord may be having issues.")
			return None
		return channel

	def get_guild(self, guild_id: int) -> dict[str, str | bool | int] :
		if not guild_id in self.data:
			self.load_guild(guild_id)
		return self.data.get(str(guild_id), {})

