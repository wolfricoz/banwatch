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
from dotenv import load_dotenv

from classes.configdata import KeyNotFound

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
def _expected_app_error_message(
		error: AppCommandError, original: Optional[BaseException]
) -> Optional[str]:
	"""Returns a user-facing message for expected errors, or None if unexpected."""
	if isinstance(error, CheckFailure):
		return "You do not have permission."
	if isinstance(original, NoPermissionException):
		return str(original)
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
		return ("The bot does not have sufficient permission to run this command. "
		        "Please check: \n* if the bot has permission to post in the channel "
		        "\n* if the bot is above the role its trying to assign\n* If trying to "
		        "ban, ensure the bot has the ban permission")
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
			logging.error(e)

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
		"""sends a message to the user if the command fails."""
		try:
			await interaction.channel.send(message)
		except Exception as e:
			logging.error(e)

	# ============================================================
	async def on_app_command_error(self, interaction: Interaction, error: AppCommandError):
		"""app command error handler."""
		original = getattr(error, "original", None)
		arguments = self._format_options(interaction)

		# Expected / user-facing errors: tell the user, don't bother Sentry.
		user_message = _expected_app_error_message(error, original)
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

		notice = f"Command failed: {error} \nreport this to Rico"
		if event_id:
			notice += f"\n(ref: `{event_id}`)"
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
