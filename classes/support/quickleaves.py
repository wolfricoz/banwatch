"""Saves a .txt file for every join-leaver: a server that added Banwatch, used it, and removed it again soon after.

For Banwatch the worry is a server that joins to read the network's ban records (lookups, checkall) and leaves, or
one that drops its bans into the network and leaves. classes.support.leavereport calls capture(); the file holds a short
summary, including the network lookups and the bans the server added, followed by every log record that mentions
the server so the trail survives after the log files rotate away. The weekly report lists the files saved that
week (saved_since), and modules.tasks removes them after QUICK_LEAVE_RETENTION_DAYS (prune).
"""
import asyncio
import logging
import os
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from classes.support.logreader import LogRecord, read_records
from database.transactions.ServerTransactions import ServerTransactions
from database.transactions.StatsTransactions import StatsTransactions

QUICK_LEAVE_DAYS = 7
QUICK_LEAVE_MIN_COMMANDS = 1
QUICK_LEAVE_DIR = os.path.join("logs", "quick_leaves")
# The files hold user names and ids copied from the logs; see compliance/05-retention-schedule.md.
QUICK_LEAVE_RETENTION_DAYS = 90
# Commands that read the network's ban records.
LOOKUP_COMMANDS = ("lookup", "checkall")

# Matches the command lines modules.logs writes for chat and app commands.
COMMAND = re.compile(r"issued (?:app)?command: `?([^`\s]+)`?")
# modules.logs buffers records for up to 30 seconds before they reach the file.
LOG_FLUSH_WAIT = 35


@dataclass
class SavedQuickLeave :
	name: str
	time_in_server: str
	commands: int
	lookups: int
	bans_added: int
	path: str


# ============================================================
def _local(moment: datetime) -> datetime :
	"""The naive local time the log formatter writes, for comparing against log records."""
	return moment.astimezone().replace(tzinfo=None) if moment.tzinfo else moment


# ============================================================
def time_in_server(seconds: float) -> str :
	minutes = int(seconds // 60)
	days, minutes = divmod(minutes, 60 * 24)
	hours, minutes = divmod(minutes, 60)
	return f"{days}d {hours}h {minutes}m" if days else f"{hours}h {minutes}m"


# ============================================================
def server_records(guild_id: int, records) -> list[LogRecord] :
	pattern = re.compile(rf"(?<!\d){guild_id}(?!\d)")
	return [record for record in records if pattern.search(record.text)]


# ============================================================
def command_counts(records: list[LogRecord]) -> Counter :
	counts = Counter()
	for record in records :
		match = COMMAND.search(record.message)
		if match :
			counts[match.group(1)] += 1
	return counts


# ============================================================
def lookup_count(commands: Counter) -> int :
	return sum(count for command, count in commands.items() if command in LOOKUP_COMMANDS)


# ============================================================
def build_file(guild_id: int, name: str, owner: str, member_count: int | None, joined_at: datetime,
               left_at: datetime, records: list[LogRecord], bans: dict) -> str :
	commands = command_counts(records)
	lines = [
		f"Server: {name} ({guild_id})",
		f"Owner: {owner}",
		f"Members: {member_count if member_count is not None else 'unknown'}",
		f"Joined: {joined_at:%Y-%m-%d %H:%M:%S %Z}".rstrip(),
		f"Left: {left_at:%Y-%m-%d %H:%M:%S %Z}".rstrip(),
		f"Time in server: {time_in_server((left_at - joined_at).total_seconds())}",
		f"Commands: {sum(commands.values())}",
		f"Network lookups: {lookup_count(commands)}",
		f"Bans added: {bans['added']}",
		f"Bans still shared: {bans['shared']}",
		"",
		"Commands used:",
		*[f"  {command}: {count}" for command, count in commands.most_common()],
		"",
		f"Log records mentioning this server ({len(records)}), in local log time:",
		"",
	]
	return "\n".join(lines) + "\n" + "".join(record.text if record.text.endswith("\n") else record.text + "\n"
	                                         for record in records)


# ============================================================
def _joined_at(guild) -> datetime | None :
	member = guild.me
	if member is not None and member.joined_at is not None :
		return member.joined_at
	# The servers row keeps the first join date, so a rejoin reads older than it is; only used as a fallback.
	server = ServerTransactions().get(guild.id)
	return server.created_at if server is not None else None


# ============================================================
def _write(guild, joined_at: datetime, left_at: datetime) -> str | None :
	records = server_records(guild.id, read_records(_local(joined_at)))
	if sum(command_counts(records).values()) < QUICK_LEAVE_MIN_COMMANDS :
		logging.info(f"{guild.name}({guild.id}) left soon after joining, but used no commands; not saved.")
		return None
	bans = StatsTransactions().bans_from_server(guild.id, joined_at)
	os.makedirs(QUICK_LEAVE_DIR, exist_ok=True)
	path = os.path.join(QUICK_LEAVE_DIR, f"{left_at:%Y-%m-%d}_{guild.id}.txt")
	owner = f"{guild.owner}({guild.owner_id})" if guild.owner else str(guild.owner_id)
	with open(path, "w", encoding="utf-8") as file :
		file.write(build_file(guild.id, guild.name, owner, guild.member_count, joined_at, left_at, records, bans))
	return path


# ============================================================
async def capture(guild) -> str | None :
	"""Saves the server's file when it removed the bot within QUICK_LEAVE_DAYS of adding it. Never raises."""
	try :
		left_at = datetime.now(tz=timezone.utc)
		joined_at = await asyncio.to_thread(_joined_at, guild)
		if joined_at is None :
			return None
		if joined_at.tzinfo is None :
			joined_at = joined_at.astimezone()
		if left_at - joined_at > timedelta(days=QUICK_LEAVE_DAYS) :
			return None
		# Let the last commands in the server reach the log file before reading it.
		await asyncio.sleep(LOG_FLUSH_WAIT)
		path = await asyncio.to_thread(_write, guild, joined_at, left_at)
		if path :
			logging.info(f"{guild.name}({guild.id}) removed Banwatch after "
			             f"{time_in_server((left_at - joined_at).total_seconds())}; saved {path}")
		return path
	except Exception as e :
		logging.error(f"Could not save the join-leaver file for {guild.id}: {e}", exc_info=True)
		return None


# ============================================================
def read_header(path: str) -> dict :
	"""The summary lines at the top of a saved file, as {label: value}."""
	header = {}
	with open(path, encoding="utf-8", errors="replace") as file :
		for line in file :
			if not line.strip() :
				break
			key, _, value = line.partition(": ")
			header[key] = value.strip()
	return header


# ============================================================
def saved_since(since: datetime, folder: str = QUICK_LEAVE_DIR) -> list[SavedQuickLeave] :
	"""The files saved since `since`, newest first."""
	if not os.path.isdir(folder) :
		return []
	saved = []
	for entry in os.scandir(folder) :
		if not entry.name.endswith(".txt") or entry.stat().st_mtime < since.timestamp() :
			continue
		try :
			header = read_header(entry.path)
			item = SavedQuickLeave(header.get("Server", entry.name), header.get("Time in server", "?"),
			                       int(header.get("Commands", "0")), int(header.get("Network lookups", "0")),
			                       int(header.get("Bans added", "0")), entry.path)
		except (OSError, ValueError) :
			continue
		saved.append((entry.stat().st_mtime, item))
	return [item for _, item in sorted(saved, key=lambda pair : pair[0], reverse=True)]


# ============================================================
def prune(now: datetime = None, folder: str = QUICK_LEAVE_DIR) -> int :
	"""Deletes files older than QUICK_LEAVE_RETENTION_DAYS."""
	if not os.path.isdir(folder) :
		return 0
	cutoff = ((now or datetime.now()) - timedelta(days=QUICK_LEAVE_RETENTION_DAYS)).timestamp()
	removed = 0
	for entry in os.scandir(folder) :
		if entry.name.endswith(".txt") and entry.stat().st_mtime < cutoff :
			os.remove(entry.path)
			removed += 1
	return removed
