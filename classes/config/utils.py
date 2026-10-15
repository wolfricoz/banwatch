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

# Names admins recognise from the commands, for keys whose stored name isn't readable as-is.
CONFIG_LABELS = {
	Channels.MOD_CHANNEL : "Mod channel",
	Channels.INVITE : "Invite channel",
	Channels.WARNING_LOG : "Warning log channel",
	Channels.WARNING_EVIDENCE_ARCHIVE : "Warning evidence archive",
	"allow_appeals" : "Ban appeals",
	"invite" : "Invite link",
	LOG_CHANGES_KEY : "Log config changes",
}
CHANNEL_KEYS = {str(c) for c in Channels}


def format_change(key, value) -> str :
	"""One readable line per change. Plain text rather than a code block, so channel and role mentions render."""
	label = CONFIG_LABELS.get(key) or str(key).replace("_", " ").capitalize()
	if value is None or value == "" :
		shown = "*removed*"
	elif str(key) in CHANNEL_KEYS and str(value).isdigit() :
		# The dashboard sends raw channel ids; the slash commands already send mentions.
		shown = f"<#{value}>"
	else :
		shown = str(value)
	return f"• **{label}** → {shown}"


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
		body = '\n'.join(format_change(key, value) for key, value in changes.items())
		await send_message(channel,
		                   f"⚙️ **Configuration changed** by {user_name}:\n"
		                   f"{body}\n"
		                   f"-# Turn these notices off with `/config toggles key:{LOG_CHANGES_KEY} action:disabled`",
		                   error_mode='ignore'
		                   )
