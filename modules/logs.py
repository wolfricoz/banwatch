"""Logs all the happenings of the bot and reports unexpected errors to Sentry.

Logging is fully non-blocking for the bot's event loop: every ``logging`` call
only enqueues a record (a cheap, thread-safe operation) via a ``QueueHandler``.
A background ``QueueListener`` thread owns the real handlers and performs all the
actual IO. File writes are additionally batched through a ``MemoryHandler`` that
is flushed to disk on a timer (see ``LOG_FLUSH_INTERVAL``), so normal activity
does not hit the disk on every log line. ERROR-level records flush immediately so
crashes are never lost.
"""
import atexit
import io
import logging
import os
import queue
import threading
import time
import traceback
from logging.handlers import MemoryHandler, QueueHandler, QueueListener, TimedRotatingFileHandler
from sys import platform
from typing import Optional

import discord.utils
import sentry_sdk
from discord import Interaction, app_commands
from discord.app_commands import AppCommandError, CheckFailure, command
from discord.ext import commands
from discord_py_utilities.exceptions import NoChannelException, NoPermissionException
from discord_py_utilities.permissions import check_missing_channel_permissions
from dotenv import load_dotenv

from classes.configdata import KeyNotFound
from classes.permissions_notice import DEFAULT_CHANNEL_PERMS, bot_role_name, format_permissions
from classes.replies import reply

# Permissions that only exist server-wide; channel permission overrides don't offer them.
SERVER_ONLY_PERMS = {"ban_members", "kick_members", "moderate_members", "manage_guild", "view_audit_log",
                     "manage_nicknames", "change_nickname", "manage_expressions", "view_guild_insights", "administrator"}

load_dotenv('main.env')

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "log.txt")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
# How often (seconds) buffered log records are flushed to disk. Clamped 5-30s.
LOG_FLUSH_INTERVAL = min(max(int(os.getenv("LOG_FLUSH_INTERVAL", "10")), 5), 30)
# Max records to buffer before forcing a flush (a safety cap; the timer normally
# drives flushing well before this is reached).
LOG_BUFFER_CAPACITY = int(os.getenv("LOG_BUFFER_CAPACITY", "5000"))
# Optional base URL to build a clickable Sentry link from an event id, e.g.
# https://your-org.sentry.io/issues/?query=
SENTRY_URL = os.getenv("SENTRY_URL")

logger = logging.getLogger('discord')

_LOGGING_CONFIGURED = False
_listener: Optional[QueueListener] = None
_memory_handler: Optional[MemoryHandler] = None
_flush_thread: Optional[threading.Thread] = None
_stop_flush = threading.Event()


# ============================================================
def _flush_loop() -> None:
	"""Periodically flushes buffered records to disk until shutdown."""
	while not _stop_flush.wait(LOG_FLUSH_INTERVAL):
		if _memory_handler is not None:
			_memory_handler.flush()


# ============================================================
def _shutdown_logging() -> None:
	"""Drains the queue and flushes any buffered records on interpreter exit."""
	_stop_flush.set()
	if _flush_thread is not None:
		_flush_thread.join(timeout=LOG_FLUSH_INTERVAL + 1)
	if _listener is not None:
		_listener.stop()  # drains remaining queued records into the memory handler
	if _memory_handler is not None:
		_memory_handler.close()  # flushes to disk, then closes the file target


# ============================================================
def setup_logging() -> None:
	"""Configures batched, non-blocking file + stream logging. Idempotent."""
	global _LOGGING_CONFIGURED, _listener, _memory_handler, _flush_thread
	if _LOGGING_CONFIGURED:
		return

	os.environ['TZ'] = 'America/New_York'
	if platform in ("linux", "linux2"):
		time.tzset()

	os.makedirs(LOG_DIR, exist_ok=True)
	formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s: %(message)s')

	# Rotates at midnight, keeps a week of history, and prunes old files for us
	# (replaces the old manual filename parsing + deletion loop). delay=True so the
	# file is only opened on first write.
	file_handler = TimedRotatingFileHandler(
		LOG_FILE, when="midnight", backupCount=7, encoding="utf-8", delay=True
	)
	file_handler.suffix = "%m-%d-%Y"
	file_handler.setFormatter(formatter)

	# Batch file writes: hold records in memory and flush on a timer (below), when
	# the buffer fills, or immediately on ERROR+. Keeps disk IO off the hot path.
	_memory_handler = MemoryHandler(
		capacity=LOG_BUFFER_CAPACITY, flushLevel=logging.ERROR, target=file_handler
	)

	stream_handler = logging.StreamHandler()
	stream_handler.setFormatter(formatter)

	# All real IO happens in the QueueListener's background thread; logging calls
	# from the event loop only enqueue a record, so they never block on disk.
	log_queue: queue.SimpleQueue = queue.SimpleQueue()
	queue_handler = QueueHandler(log_queue)

	root = logging.getLogger()
	for handler in root.handlers[:]:
		root.removeHandler(handler)
	root.addHandler(queue_handler)
	root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

	_listener = QueueListener(
		log_queue, _memory_handler, stream_handler, respect_handler_level=True
	)
	_listener.start()

	_stop_flush.clear()
	_flush_thread = threading.Thread(target=_flush_loop, name="log-flush", daemon=True)
	_flush_thread.start()
	atexit.register(_shutdown_logging)

	logging.getLogger('discord').setLevel(logging.INFO)
	logging.getLogger('sqlalchemy').setLevel(logging.WARN)

	logging.info(
		"\n----------------------------------------------------"
		"\nbot started at: %s\n"
		"----------------------------------------------------",
		time.strftime('%c %Z'),
	)
	_LOGGING_CONFIGURED = True


# Errors that are the user's fault / expected and should NOT be reported to
# Sentry. Each maps to a friendly message shown to the user instead.
def _no_permission_message(exc: NoPermissionException) -> str:
	"""Turns discord_py_utilities' raw 'Missing permission to send message: view_channel, ...' into labels."""
	text = str(exc)
	prefix = "Missing permission to send message: "
	if not text.startswith(prefix):
		return text
	perms = [p.strip() for p in text[len(prefix):].split(",") if p.strip() and "context" not in p]
	if not perms:
		return ("❌ I couldn't post my reply because I'm missing permissions in the channel. "
		        "Run `/config permissioncheck` to see what's missing.")
	return (f"❌ I couldn't post my reply because I'm missing {format_permissions(perms)} in that channel.\n"
	        "Open the channel → **Edit Channel → Permissions**, add my role, enable those, then try again.")


def _forbidden_message(interaction: Optional[Interaction]) -> str:
	"""Explains a raw 403. Discord doesn't say which permission was missing, so don't claim to know: a 403 from
	e.g. guild.bans() in a channel the bot also can't post in used to be blamed on the channel permissions."""
	message = ("❌ Discord blocked this action: I'm missing a permission it needs, or my role is below the role of "
	           "the member I'm acting on.\nRun `/config permissioncheck` to see what's missing.")
	channel = getattr(interaction, "channel", None)
	guild = getattr(interaction, "guild", None)
	if guild is not None and isinstance(channel, (discord.abc.GuildChannel, discord.Thread)):
		missing = check_missing_channel_permissions(channel, DEFAULT_CHANNEL_PERMS)
		if missing:
			message += (f"\nIn {channel.mention} I'm also missing {format_permissions(missing)}, so commands that "
			            "post here won't work either.")
	return message


def _expected_app_error_message(
		error: AppCommandError, original: Optional[BaseException], interaction: Optional[Interaction] = None
) -> Optional[str]:
	"""Returns a user-facing message for expected errors, or None if unexpected."""
	# Both permission errors subclass CheckFailure, so they must be matched before it.
	if isinstance(error, app_commands.BotMissingPermissions):
		role = bot_role_name(interaction.guild) if getattr(interaction, "guild", None) else "my role"
		# Server-level permissions like Ban Members don't exist in channel overrides, so only offer that route
		# when at least one of the missing permissions can actually be set on a channel.
		channel_route = (" (or in this channel's permissions)"
		                 if not set(error.missing_permissions) <= SERVER_ONLY_PERMS else "")
		return (f"❌ I'm missing {format_permissions(error.missing_permissions)}, which this command needs.\n"
		        f"Enable it under **Server Settings → Roles → {role}**{channel_route}, then try again.")
	if isinstance(error, app_commands.MissingPermissions):
		return f"❌ You need {format_permissions(error.missing_permissions)} to use this command."
	if isinstance(error, CheckFailure):
		return "❌ You do not have permission to use this command."
	if isinstance(original, NoPermissionException):
		return _no_permission_message(original)
	if isinstance(original, KeyNotFound):
		return str(original)
	if isinstance(original, NoChannelException):
		return ("No channel set or does not exist, check the Config or fill in the "
		        "required arguments.")
	if isinstance(error, app_commands.TransformerError):
		return ("Failed to transform given input to member, please select the user "
		        "from the list, or use the user's ID.")
	if isinstance(error, commands.MemberNotFound):
		return "Member not found."
	if isinstance(original, discord.Forbidden):
		return _forbidden_message(interaction)
	return None


class Logging(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	# ============================================================
	@staticmethod
	def _format_options(interaction: Interaction) -> str:
		"""Renders the slash-command options as a readable string."""
		try:
			data = [f"{a['name']}: {a['value']}" for a in interaction.data['options']]
			return ", ".join(data)
		except (KeyError, TypeError):
			return "No data"

	# ============================================================
	def _capture(self, error: BaseException, *, guild, user, command_name: Optional[str],
	             arguments: str) -> Optional[str]:
		"""Reports an unexpected error to Sentry with context, returns the event id."""
		with sentry_sdk.new_scope() as scope:
			if guild is not None:
				scope.set_tag("guild.id", guild.id)
				scope.set_context("guild", {"name": guild.name, "id": guild.id})
			if user is not None:
				scope.set_user({"id": user.id, "username": str(user)})
			if command_name is not None:
				scope.set_tag("command", command_name)
			scope.set_context("command", {"name": command_name, "arguments": arguments})
			return sentry_sdk.capture_exception(error)

	# ============================================================
	async def _notify_dev(self, header: str, event_id: Optional[str], tb: str) -> None:
		"""Posts an error to the DEV channel with a Sentry reference (or file fallback)."""
		channel = self.bot.get_channel(self.bot.DEV)
		if channel is None:
			return
		try:
			if event_id:
				reference = f"\nSentry event: `{event_id}`"
				if SENTRY_URL:
					reference += f"\n{SENTRY_URL}{event_id}"
				await channel.send(f"{header}{reference}")
			else:
				# Sentry not configured / capture failed: fall back to a traceback file
				# built in memory (no shared error.txt on disk, no race).
				attachment = discord.File(io.BytesIO(tb.encode("utf-8")), "error.txt")
				await channel.send(header, file=attachment)
		except Exception as e:
			logging.error(f"Could not post the error to the DEV channel: {e}", exc_info=True)

	# ============================================================
	@commands.Cog.listener("on_command_error")
	async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
		"""handles chat-based command errors."""
		if isinstance(error, commands.MissingRequiredArgument):
			return await ctx.send("Please fill in the required arguments")
		if isinstance(error, commands.CommandNotFound):
			return
		if isinstance(error, commands.CheckFailure):
			return await ctx.send("You do not have permission")
		if isinstance(error, commands.MemberNotFound):
			return await ctx.send("Member not found")

		# Unexpected -> Sentry + DEV channel
		guild = ctx.guild
		command_name = ctx.command.name if ctx.command else "unknown"
		guild_label = f"{guild.name} {guild.id}" if guild else f"DM {ctx.author.id}"
		event_id = self._capture(error, guild=guild, user=ctx.author,
		                         command_name=command_name, arguments="")
		logger.warning(f"\n{guild_label} {command_name}: {error}")
		header = f"{guild_label}: {ctx.author}: {command_name}"
		await self._notify_dev(header, event_id, traceback.format_exc())

	# ============================================================
	def cog_load(self):
		tree = self.bot.tree
		self._old_tree_error = tree.on_error
		tree.on_error = self.on_app_command_error

	# ============================================================
	def cog_unload(self):
		tree = self.bot.tree
		tree.on_error = self._old_tree_error

	# ============================================================
	async def on_fail_message(self, interaction: Interaction, message: str):
		"""Tells the user the command failed, privately and without needing channel permissions."""
		if not await reply(interaction, message):
			logging.warning(f"Could not tell {interaction.user} that their command failed: {message}")

	# ============================================================
	async def on_app_command_error(self, interaction: Interaction, error: AppCommandError):
		"""app command error handler."""
		original = getattr(error, "original", None)
		arguments = self._format_options(interaction)

		# Expected / user-facing errors: tell the user, don't bother Sentry.
		user_message = _expected_app_error_message(error, original, interaction)
		if user_message is not None:
			return await self.on_fail_message(interaction, user_message)

		# Unexpected -> Sentry + DEV channel + user notice.
		guild = interaction.guild
		command_name = interaction.command.name if interaction.command else "unknown"
		guild_label = f"{guild.name} {guild.id}" if guild else f"DM {interaction.user.id}"

		event_id = self._capture(error, guild=guild, user=interaction.user,
		                         command_name=command_name, arguments=arguments)
		logger.warning(
			f"\n{guild_label} {command_name} with arguments {arguments}: "
			f"{traceback.format_exc()}")
		header = (f"{guild_label}: {interaction.user}: {command_name} "
		          f"with arguments {arguments}")
		await self._notify_dev(header, event_id, traceback.format_exc())

		# The developers already have the traceback (Sentry / DEV channel), so keep internals out of the user's view.
		notice = ("❌ Something went wrong while running this command. The developers have been notified "
		          "automatically.\nIf it keeps happening, report it with `/support bug`")
		notice += f" and include this reference: `{event_id}`" if event_id else "."
		await self.on_fail_message(interaction, notice)

	# ============================================================
	@commands.Cog.listener(name='on_command')
	async def log_command(self, ctx: commands.Context):
		"""logs every chat command when initiated."""
		server = ctx.guild
		user = ctx.author
		command_name = ctx.command.name if ctx.command else "unknown"
		location = f"{server.name}({server.id})" if server else f"DM({user.id})"
		logging.info(f"{location}: {user}({user.id}) issued command: {command_name}")
		sentry_sdk.add_breadcrumb(
			category="command", level="info",
			message=f"{command_name} by {user} in {location}")

	# ============================================================
	@commands.Cog.listener(name='on_app_command_completion')
	async def log_app_command(self, interaction: Interaction, command_name: command):
		"""logs every app command when finished."""
		server = interaction.guild
		user = interaction.user
		location = f"{server.name}({server.id})" if server else f"DM({user.id})"
		arguments = self._format_options(interaction)
		logging.info(
			f"{location}: {user}({user.id}) issued appcommand: `{command_name.name}` "
			f"with arguments: {arguments}")
		sentry_sdk.add_breadcrumb(
			category="command", level="info",
			message=f"{command_name.name} by {user} in {location}",
			data={"arguments": arguments})


# ============================================================
async def setup(bot):
	"""Adds the cog to the bot."""
	setup_logging()
	await bot.add_cog(Logging(bot))
