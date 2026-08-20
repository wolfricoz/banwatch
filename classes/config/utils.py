"""Telling a server when its Banwatch configuration changed.

Configuration can be changed from two places - the slash commands and the website dashboard -
and until now neither left a trace in the server itself. A setting could be changed (or wiped)
by anyone with Manage Server, from a browser, and the only way to notice was that Banwatch had
quietly stopped doing something.

Mirrors ageverifier's classes/config/utils.py: same toggle key, same message format, same
"never raise" contract. The one deliberate difference is where the notice goes - Banwatch has
no approval channel, so it uses the mod channel, which is the channel Banwatch already talks
to staff in.
"""
import logging
from abc import ABC, abstractmethod

import discord
from discord_py_utilities.messages import send_message

from classes.configdata import ConfigData
from data.config.mappings import Channels

# Unlike ageverifier, Banwatch does not seed per-guild toggle rows, so an unset key has to mean
# "on" here or nobody would ever see one of these. Turning it off writes an explicit DISABLED.
LOG_CHANGES_KEY = "log_config_changes"


class ConfigUtils(ABC) :

	@staticmethod
	@abstractmethod
	async def log_change(guild: discord.Guild, changes: dict, user_name: str = None,
	                     channel: discord.TextChannel = None) :
		guild_id = guild.id
		logging.info(f"Configuration changed in guild {guild_id}: {changes} by user {user_name}")
		if not ConfigData().get_toggle(guild_id, LOG_CHANGES_KEY, default="ENABLED") :
			logging.info("Logging of configuration changes is disabled.")
			return
		logging.info("Logging of configuration changes is enabled.")
		if not channel :
			modchannel = ConfigData().get_key_int_or_zero(guild_id, Channels.MOD_CHANNEL)
			channel = guild.get_channel(modchannel)
		if channel is None :
			logging.info("No mod channel found for logging configuration changes.")
			return
		body = '\n'.join(
			f"{key}: {value if value else 'This key was removed'}" for key, value in changes.items())
		await send_message(channel,
		                   f"[CONFIG CHANGE] {user_name} changed the configuration:\n"
		                   f"```{body}```\n"
		                   f"-# this setting can be turned off with `/config toggles key:{LOG_CHANGES_KEY} action:disabled`",
		                   error_mode='ignore'
		                   )
