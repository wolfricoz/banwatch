"""The weekly developer stats report, posted to the DEV channel on Sundays by modules.tasks.

Everything here comes from data Banwatch already keeps: the database (database.transactions.StatsTransactions),
the log files (classes.support.logreader) and the join-leaver files (classes.support.quickleaves). collect()
gathers it, build_embeds() only formats it so it can be tested without a bot, and send() posts it.
"""
import asyncio
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import discord

from classes.queue import queue
from classes.support import quickleaves
from classes.support.logreader import read_records
from database.transactions.StatsTransactions import StatsTransactions

TOP_SERVERS = 5
FIELD_LIMIT = 1024
# Written by main.on_guild_join and main.on_guild_remove; the servers table keeps no leave date.
JOINED = re.compile(r" joined, refreshing ban list$")
LEFT = re.compile(r" left, refreshing ban list$")
# Module import happens while the cogs load, which is close enough to the bot's start for an uptime figure.
_loaded = datetime.now(tz=timezone.utc)


@dataclass
class LogSummary :
	errors: int = 0
	warnings: int = 0
	joins: int = 0
	leaves: int = 0
	top_errors: list[tuple[str, int]] = field(default_factory=list)


@dataclass
class WeeklyReport :
	start: datetime
	end: datetime
	bans: dict
	previous_bans: dict
	review: dict
	top_servers: list[tuple[str, int]]
	appeals: dict
	previous_appeals: dict
	warnings: dict
	servers: dict
	guilds_connected: int
	latency_ms: int | None
	queue_status: str
	online_since: datetime
	logs: LogSummary
	quick_leaves: list[quickleaves.SavedQuickLeave] = field(default_factory=list)


# ============================================================
def summarise_logs(start: datetime, paths: list[str] = None) -> LogSummary :
	"""Counts errors, warnings, server joins and leaves logged since start, and the most common errors."""
	summary = LogSummary()
	messages = Counter()
	for record in read_records(start, paths) :
		if record.level == "WARNING" :
			summary.warnings += 1
		elif record.level in ("ERROR", "CRITICAL") :
			summary.errors += 1
			# Ids and counts would make every occurrence of the same error unique.
			messages[re.sub(r"\d+", "#", record.message.strip())[:90]] += 1
		elif JOINED.search(record.message) :
			summary.joins += 1
		elif LEFT.search(record.message) :
			summary.leaves += 1
	summary.top_errors = messages.most_common(3)
	return summary


# ============================================================
def _collect_database(start: datetime, end: datetime) -> dict :
	stats = StatsTransactions()
	previous = start - (end - start)
	return {
		"bans"             : stats.bans(start, end),
		"previous_bans"    : stats.bans(previous, start),
		"review"           : stats.review_queue(end),
		"top_servers"      : stats.top_servers(start, end, TOP_SERVERS),
		"appeals"          : stats.appeals(start, end, end),
		"previous_appeals" : stats.appeals(previous, start, end),
		"warnings"         : stats.warnings(start, end),
		"servers"          : stats.servers(start, end, end),
	}


# ============================================================
async def collect(bot, now: datetime = None, days: int = 7) -> WeeklyReport :
	end = now or datetime.now(tz=timezone.utc)
	start = end - timedelta(days=days)
	data = await asyncio.to_thread(_collect_database, start, end)
	# Log records carry naive local times.
	local_start = start.astimezone().replace(tzinfo=None)
	logs = await asyncio.to_thread(summarise_logs, local_start)
	quick_leaves = await asyncio.to_thread(quickleaves.saved_since, start)
	latency = bot.latency
	return WeeklyReport(
		start=start, end=end, **data,
		guilds_connected=len(bot.guilds),
		latency_ms=round(latency * 1000) if latency == latency and latency != float("inf") else None,
		queue_status=str(queue().status()),
		online_since=_loaded,
		logs=logs,
		quick_leaves=quick_leaves,
	)


# ============================================================
def delta(current: int, previous: int) -> str :
	"""The change against the previous week, e.g. '▲ 12%'."""
	if not previous :
		return "—" if not current else "new"
	change = round((current - previous) / previous * 100)
	if change == 0 :
		return "± 0%"
	return f"{'▲' if change > 0 else '▼'} {abs(change)}%"


# ============================================================
def rate(part: int, whole: int) -> str :
	return f"{part / whole:.0%}" if whole else "—"


# ============================================================
def duration(age: timedelta | None) -> str :
	if age is None :
		return "—"
	minutes = int(age.total_seconds() // 60)
	days, minutes = divmod(minutes, 60 * 24)
	hours, minutes = divmod(minutes, 60)
	if days :
		return f"{days}d {hours}h"
	if hours :
		return f"{hours}h {minutes}m"
	return f"{minutes}m"


# ============================================================
def _field(embed: discord.Embed, name: str, lines: list[str]) :
	value = "\n".join(lines) or "—"
	if len(value) > FIELD_LIMIT :
		value = value[:FIELD_LIMIT - 1] + "…"
	embed.add_field(name=name, value=value, inline=False)


# ============================================================
def _row(label: str, current: int, previous: int = None) -> str :
	if previous is None :
		return f"{label}: **{current:,}**"
	return f"{label}: **{current:,}** ({delta(current, previous)})"


# ============================================================
def build_embeds(report: WeeklyReport) -> list[discord.Embed] :
	period = f"{report.start:%b %d} – {report.end:%b %d, %Y}"
	b, pb, review = report.bans, report.previous_bans, report.review

	network = discord.Embed(title="📊 Weekly stats", description=f"{period} · change vs the week before",
	                        color=discord.Color.blue())
	_field(network, "Ban network", [
		_row("Bans recorded", b["new"], pb["new"]),
		f"With evidence: **{b['with_proof']:,}** ({rate(b['with_proof'], b['new'])}, "
		f"last week {rate(pb['with_proof'], pb['new'])})",
		f"Hidden: **{b['hidden']:,}** · Verified: **{b['verified']:,}**",
		_row("Bans removed (unbanned)", b["removed"], pb["removed"]),
	])
	_field(network, "Review queue", [
		_row("Waiting for review now", review["waiting"]),
		f"Oldest waiting: **{duration(review['oldest_age'])}**",
	])
	_field(network, f"Top {len(report.top_servers)} servers by bans recorded" if report.top_servers else "Top servers",
	       [f"{i}. {discord.utils.escape_markdown(name or 'unknown')[:60]}: **{total:,}**"
	        for i, (name, total) in enumerate(report.top_servers, start=1)])

	a, pa, w = report.appeals, report.previous_appeals, report.warnings
	appeals = discord.Embed(title="⚖️ Appeals & warnings", color=discord.Color.teal())
	_field(appeals, "Appeals", [
		_row("Opened", a["new"], pa["new"]),
		f"Approved: **{a['approved']:,}** · Denied: **{a['denied']:,}** "
		f"(approval rate {rate(a['approved'], a['approved'] + a['denied'])})",
		_row("Appeal messages", a["messages"], pa["messages"]),
		f"Pending now: **{a['pending']:,}**, oldest **{duration(a['oldest_age'])}**",
	])
	_field(appeals, "Warnings", [
		f"Issued: **{w['new']:,}** · Evidence pieces: **{w['evidence']:,}**",
	])

	s, logs = report.servers, report.logs
	health = discord.Embed(title="🛠️ Servers & health", color=discord.Color.dark_grey())
	drift = s["active"] - report.guilds_connected
	_field(health, "Servers", [
		f"Joined: **{logs.joins:,}** · Left: **{logs.leaves:,}** · New to Banwatch: **{s['new']:,}**",
		f"Active: **{s['active']:,}** ({s['members']:,} members, {s['hidden']:,} hidden)",
		f"Connected guilds: **{report.guilds_connected:,}**" + (f" ⚠️ {drift:+} vs the database" if drift else ""),
		_row("Premium expiring in 7 days", s["premium_expiring"]),
	])
	quick = [f"**{len(report.quick_leaves)}** server(s) removed Banwatch within {quickleaves.QUICK_LEAVE_DAYS} days "
	         f"after using it · files in `{quickleaves.QUICK_LEAVE_DIR}`"]
	for item in report.quick_leaves[:5] :
		flags = []
		if item.lookups :
			flags.append(f"🔍 {item.lookups} lookup(s)")
		if item.bans_added :
			flags.append(f"🔨 {item.bans_added} ban(s) added")
		quick.append(f"{discord.utils.escape_markdown(item.name)[:80]}: {item.time_in_server}, "
		             f"{item.commands} command(s)" + (f" · {' · '.join(flags)}" if flags else ""))
	if len(report.quick_leaves) > 5 :
		quick.append(f"…and {len(report.quick_leaves) - 5} more")
	_field(health, "Join-leavers", quick)
	errors = [
		f"Online since: {discord.utils.format_dt(report.online_since, 'R')}",
		f"Latency: **{report.latency_ms} ms**" if report.latency_ms is not None else "Latency: —",
		f"Queue: {discord.utils.escape_markdown(report.queue_status)[:200]}",
		f"Logged errors: **{logs.errors:,}** · warnings: **{logs.warnings:,}**",
	]
	errors += [f"`{count}×` {discord.utils.escape_markdown(message)}" for message, count in logs.top_errors]
	_field(health, "Bot health", errors)
	health.set_footer(text="Appeal decisions are dated by the appeal's last update.")
	return [network, appeals, health]


# ============================================================
async def send(bot, now: datetime = None) -> bool :
	"""Posts the report to the DEV channel. Returns False when it could not be posted."""
	channel = bot.get_channel(bot.DEV)
	if channel is None :
		logging.warning("Weekly report skipped: the DEV channel could not be found.")
		return False
	try :
		report = await collect(bot, now)
		await channel.send(embeds=build_embeds(report))
		return True
	except Exception as e :
		logging.error(f"Weekly report could not be sent: {e}", exc_info=True)
		return False
