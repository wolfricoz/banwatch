"""Posts a summary to the ban approval channel whenever Banwatch is removed from a server.

main.on_guild_remove starts send() as a task. It runs quickleaves.capture() first, so a join-leaver's summary also
carries the commands and network lookups from its saved file, with the file attached. capture() waits for the log
buffer to flush only for join-leavers; every other leave is reported straight away.
"""
import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import discord
from discord_py_utilities.messages import send_message

from classes.configer import Configer
from classes.support import quickleaves
from database.transactions.ServerTransactions import ServerTransactions
from database.transactions.StatsTransactions import StatsTransactions

# A servers row this much older than the bot's join date means the server had removed Banwatch before.
REJOIN_MARGIN = timedelta(hours=1)


@dataclass
class LeaveInfo :
	joined_at: datetime | None
	left_at: datetime
	first_added: datetime | None
	bans: dict | None
	shared_total: int
	premium: datetime | None
	hidden: bool
	blacklisted: bool
	quick_leave: dict | None = None


# ============================================================
def _aware(moment: datetime | None) -> datetime | None :
	# MySQL hands back naive datetimes even for timezone columns.
	if moment is not None and moment.tzinfo is None :
		return moment.astimezone()
	return moment


# ============================================================
def _stamp(moment: datetime, style: str = "f") -> str :
	return f"<t:{int(moment.timestamp())}:{style}>"


# ============================================================
def _gather(guild, left_at: datetime) -> LeaveInfo :
	joined_at = _aware(quickleaves._joined_at(guild))
	server = ServerTransactions().get(guild.id)
	return LeaveInfo(
		joined_at=joined_at,
		left_at=left_at,
		first_added=_aware(server.created_at) if server else None,
		bans=StatsTransactions().bans_from_server(guild.id, joined_at) if joined_at else None,
		shared_total=len(ServerTransactions().get_bans(guild.id, uid_only=True)),
		premium=_aware(server.premium) if server else None,
		hidden=bool(server.hidden) if server else False,
		blacklisted=False,
	)


# ============================================================
def build_embed(guild, info: LeaveInfo, bot_count: int) -> discord.Embed :
	embed = discord.Embed(title=f"Left {guild.name}", color=discord.Color.red(),
	                      description=f"Banwatch was removed from `{guild.name}` ({guild.id}). "
	                                  f"Ban watch is now in {bot_count} servers.")
	owner = f"{guild.owner}({guild.owner_id})" if guild.owner else str(guild.owner_id)
	embed.add_field(name="Owner", value=f"`{owner}`", inline=False)
	embed.add_field(name="Members", value=guild.member_count if guild.member_count is not None else "unknown")
	embed.add_field(name="Server created", value=_stamp(guild.created_at, "D"))

	if info.joined_at :
		stay = quickleaves.time_in_server((info.left_at - info.joined_at).total_seconds())
		embed.add_field(name="Joined", value=_stamp(info.joined_at))
		embed.add_field(name="Time in server", value=stay)
	else :
		embed.add_field(name="Joined", value="unknown")
	if info.first_added and info.joined_at and info.joined_at - info.first_added > REJOIN_MARGIN :
		embed.add_field(name="First added", value=f"{_stamp(info.first_added, 'D')} (this was a rejoin)")

	if info.bans is not None :
		embed.add_field(name="Bans added this stay",
		                value=f"{info.bans['added']} ({info.bans['shared']} still shared)")
	embed.add_field(name="Shared bans (all time)", value=info.shared_total)

	flags = []
	if info.premium and info.premium > info.left_at :
		flags.append(f"Premium until {_stamp(info.premium, 'D')}")
	if info.hidden :
		flags.append("Hidden server")
	if info.blacklisted :
		flags.append("Blacklisted")
	if flags :
		embed.add_field(name="Flags", value="\n".join(flags), inline=False)

	if info.quick_leave is not None :
		embed.add_field(name="⚠️ Join-leaver",
		                value=f"Removed within {quickleaves.QUICK_LEAVE_DAYS} days of joining. "
		                      f"Commands: {info.quick_leave.get('Commands', '?')} · "
		                      f"Network lookups: {info.quick_leave.get('Network lookups', '?')}. "
		                      f"The log trail is attached.",
		                inline=False)
	embed.set_footer(text=guild.id)
	return embed


# ============================================================
async def send(bot, guild) -> None :
	"""Posts the leave summary to the ban approval channel. Never raises."""
	try :
		left_at = datetime.now(tz=timezone.utc)
		path = await quickleaves.capture(guild)
		info = await asyncio.to_thread(_gather, guild, left_at)
		info.blacklisted = bool(await Configer.is_blacklisted(guild.id))
		if path :
			info.quick_leave = await asyncio.to_thread(quickleaves.read_header, path)

		channel = bot.get_channel(int(os.getenv("BANS")))
		if channel is None :
			logging.warning(f"Could not post the leave summary for {guild.id}: the ban approval channel is not cached.")
			return
		file = discord.File(path, filename=os.path.basename(path)) if path else None
		await send_message(channel, embed=build_embed(guild, info, len(bot.guilds)), files=[file] if file else None)
	except Exception as e :
		logging.error(f"Could not post the leave summary for {guild.id}: {e}", exc_info=True)
