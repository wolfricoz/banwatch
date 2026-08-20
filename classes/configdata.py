"""This class is for the guild's Config data, which is stored in the database. It is used to store and retrieve data from the database."""
import asyncio
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


# The config table stores everything as a string, and three different vocabularies for the same
# boolean have accumulated: "ENABLED"/"DISABLED" (legacy and ageverifier), "true"/"false" (what
# the dashboard writes) and "1"/"0". Normalise all of them in one place - the previous check
# lowercased the value and then compared it against the *uppercase* literals "ENABLED"/"DISABLED",
# which can never match, so a disabled toggle came back as the truthy string "disabled".
TRUE_VALUES = frozenset({"true", "1", "on", "enabled", "yes"})
FALSE_VALUES = frozenset({"false", "0", "off", "disabled", "no"})


class ConfigData(metaclass=Singleton) :
	"""This class generates the Config file, with functions to change and get values from it"""

	configcontroller = ConfigTransactions()
	# guild id (as a *string*) -> {KEY: value}. Always go through get_guild/load_guild rather than
	# indexing this directly: mixing int and str keys is what silently disabled the cache before.
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

	# ============================================================
	# os.rmdir("configs")
	def reload(self) :
		"""Drops the whole cache; every guild is re-read from the database on next access.

		Deliberately lazy. Eagerly re-loading every known guild here was one query per guild
		on every dashboard save, and all but the one guild that actually changed would be
		thrown away unread."""
		self.data = {}

	# ============================================================
	def load(self, guilds) :
		self.data = {}
		for guild in guilds :
			self.load_guild(guild.id)

	# ============================================================
	def load_guild(self, serverid) :
		"""Loads the Config for a guild"""
		config = self.configcontroller.server_config_get(serverid)
		self.data[str(serverid)] = {}

		for item in config :
			self.data[str(serverid)][item.key.upper()] = item.value
		return self.data[str(serverid)]

	# ============================================================
	def add_key(self, serverid, key, value: str | bool | int, overwrite=False) :
		"""Adds a key to the Config"""

		self.configcontroller.config_unique_add(serverid, key, value, overwrite=overwrite)
		self.load_guild(serverid)

	# ============================================================
	def remove_key(self, serverid, key) :
		"""Removes a key from the Config"""
		self.configcontroller.config_unique_remove(serverid, key)
		self.load_guild(serverid)

	# ============================================================
	def update_key(self, serverid, key, value) :
		"""Updates a key in the Config"""
		self.configcontroller.config_update(serverid, key, value)
		self.load_guild(serverid)

	# ============================================================
	def get_key(self, serverid, key, default=None) :
		"""Gets a key from the Config, throws KeyNotFound if not found"""
		guild = self.get_guild(serverid)
		value = guild.get(key.upper(), default)
		if not value:
			return default

		if isinstance(value, bool) :
			return value
		if not isinstance(value, str) :
			# The column is a string, but a bool/int written straight through the ORM comes back
			# as-is. Hand it back rather than calling str-only methods on it.
			return value

		normalised = value.strip().lower()
		# Booleans first: "1"/"0" are boolean spellings here, which is why they were excluded
		# from the numeric branch below.
		if normalised in TRUE_VALUES :
			return True
		if normalised in FALSE_VALUES :
			return False
		if value.strip().isnumeric() :
			return int(value.strip())

		return value

	# ============================================================
	def get_toggle(self, serverid: int, key: str, expected: str = "ENABLED", default: str = "DISABLED") -> bool :
		"""Reads a key as an on/off toggle, tolerating every spelling in TRUE_VALUES/FALSE_VALUES.

		:param expected: the state being asked about - ``get_toggle(g, k)`` answers "is this on?"
		:param default: what an unset key counts as.
		"""
		value = str(self.get_key(serverid, key, default)).strip().lower()

		if value in TRUE_VALUES :
			return expected.upper() == "ENABLED"
		if value in FALSE_VALUES :
			return expected.upper() == "DISABLED"
		return value == expected.lower()

	# ============================================================
	def get_key_int_or_zero(self, serverid: int, key: str) -> int :
		"""Gets a key as an int, returning 0 when it is unset or not a usable id."""
		result = self.get_key(serverid, key)
		# bool is a subclass of int, so check it first or a stored "false" returns 0/1 as an id.
		if isinstance(result, bool) :
			return 0
		if isinstance(result, int) :
			return result
		if isinstance(result, str) and result.strip().isnumeric() :
			return int(result.strip())
		if result is not None :
			logging.warning(f"{serverid} key {key} is not an int")
		return 0



	# ============================================================
	def get_key_or_none(self, serverid, key) :
		"""Gets a key from the Config, returns None if not found"""
		return self.get_key(serverid, key)

		"""Gets channel from the Config."""

	# ============================================================
	async def get_channel(self, guild: discord.Guild, channel_type: str = "modchannel", optional: bool = False) -> None | VoiceChannel | StageChannel | ForumChannel | TextChannel | CategoryChannel | Thread :
		"""Gets the channel from the Config"""
		channel_id = self.get_key_or_none(guild.id, channel_type)
		# bool is a subclass of int, so `isinstance(channel_id, int)` is True for True/False and a
		# bare int check would let them straight through as a channel id. get_key coerces stored
		# "false"/"0"/"disabled" values to the boolean False, so an unset channel arrives here as
		# False, not None - which Discord then rejects with 'Value "False" is not snowflake'.
		if isinstance(channel_id, bool) or not isinstance(channel_id, int) :
			if isinstance(channel_id, str) and channel_id.isnumeric() :
				channel_id = int(channel_id)
			else :
				channel_id = None

		if channel_id is None :
			channel = find_first_accessible_text_channel(guild)
			if channel is None:
				channel = guild.owner
			if optional:
				return None
			await send_message(channel,
			                   f"No `{channel_type}` channel set for {guild.name}, please set it up using the /Config command")
			return None
		channel = guild.get_channel(channel_id)

		if channel is None :
			# NOTE: this was previously a `while attempts < 3` loop whose counter was never
			# incremented, and whose NotFound handler did a bare `continue`. A configured channel
			# that had been deleted therefore looped forever, re-issuing the same doomed fetch and
			# hanging the entire ban sweep on that one guild. Retry only what retrying can fix.
			for attempt in range(3):
				try:
					channel = await guild.fetch_channel(channel_id)
					break
				except discord.NotFound:
					# The channel genuinely does not exist - retrying cannot bring it back.
					logging.info(
						f"Configured `{channel_type}` channel {channel_id} no longer exists in "
						f"{guild.name}({guild.id})")
					break
				except discord.Forbidden:
					# We can see it but not access it; also not something a retry resolves.
					logging.info(
						f"No access to `{channel_type}` channel {channel_id} in {guild.name}({guild.id})")
					break
				except discord.HTTPException as e:
					# Only 5xx and rate limits are worth retrying. A 4xx means the request itself is
					# wrong (a malformed id, say) and will fail identically every time - retrying it
					# just burns three API calls and two seconds per guild, per sweep.
					retryable = e.status >= 500 or e.status == 429
					logging.warning(
						f"Failed to fetch `{channel_type}` channel {channel_id} in "
						f"{guild.name}({guild.id}) (attempt {attempt + 1}/3, status {e.status}, "
						f"{'retrying' if retryable and attempt < 2 else 'giving up'}): {e}")
					if not retryable or attempt == 2:
						return None
					await asyncio.sleep(1)
		if channel is None :
			if optional:
				return None
			channel = find_first_accessible_text_channel(guild)
			if channel is None:
				channel = guild.owner
			await send_message(channel,
			                   f"Banwatch could not fetch the `{channel_type}` channel with id {channel_id} in {guild.name}, please verify it exists and is accessible by the bot. If it does then discord may be having issues.")
			return None
		return channel

	# ============================================================
	def get_guild(self, guild_id: int) -> dict[str, str | bool | int] :
		# The cache is keyed by str(guild_id) because load_guild writes it that way. Testing
		# membership with the raw int - which is what this did - never matched, so every single
		# get_key() fell through to load_guild() and hit the database. That made the cache dead
		# weight and turned the config into an accidental live read; it also meant the refresh
		# endpoint had nothing to invalidate. Compare like for like.
		cache_key = str(guild_id)
		if cache_key not in self.data :
			return self.load_guild(guild_id)
		return self.data[cache_key]

