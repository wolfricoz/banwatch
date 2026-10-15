"""Re-checks the bans the network can see against the current auto-hide rules, for modules.tasks.

BanChecker only judges a ban when it comes in. A ban that got past an older, looser version of the
rules - or past a path that skipped them - stays shared until someone notices it. This finds those
bans and reports them to the DEV channel.

It never hides anything itself: a rule that turns out too broad must not silently pull hundreds of
legitimate bans from the network. Staff read the report and hide the ones they agree with using
/staff banvisibility. find_flagged() and build_report() take plain data so they can be tested
without a bot; send() posts the result.
"""
import asyncio
import io
import logging
from dataclasses import dataclass

import discord

from classes.ban.BanChecker import BanChecker
from database.transactions.BanTransactions import BanTransactions

# Discord rejects messages over 2000 characters; the full list goes in the attached file.
PREVIEW_LINES = 10
REASON_PREVIEW = 80


@dataclass
class FlaggedBan :
	ban_id: int
	guild: str
	rule: str
	reason: str
	verified: bool
	edited_by: str | None


# ============================================================
async def find_flagged(bans) -> list[FlaggedBan] :
	"""Runs the string-only auto-hide rules over ban rows and returns the ones that fail them."""
	flagged = []
	for count, ban in enumerate(bans, 1) :
		if count % 500 == 0 :
			await asyncio.sleep(0)
		rule = await BanChecker.auto_hide_verdict(ban.reason)
		if rule is None :
			continue
		guild = ban.guild.name if ban.guild is not None else str(ban.gid)
		flagged.append(FlaggedBan(ban.ban_id, guild, rule, ban.reason or "", bool(ban.verified), ban.edited_by))
	return flagged


# ============================================================
def _line(ban: FlaggedBan, reason_length: int = None) -> str :
	reason = " ".join(ban.reason.split())
	if reason_length and len(reason) > reason_length :
		reason = reason[:reason_length - 1] + "…"
	notes = [note for note, on in (("verified", ban.verified), (f"edited by {ban.edited_by}", ban.edited_by)) if on]
	suffix = f" ({', '.join(notes)})" if notes else ""
	return f"{ban.ban_id} | {ban.rule} | {ban.guild} | {reason}{suffix}"


# ============================================================
def build_report(flagged: list[FlaggedBan], scanned: int) -> tuple[str, str] :
	"""The DEV channel message and the full list for the attached file."""
	by_rule = {}
	for ban in flagged :
		by_rule[ban.rule] = by_rule.get(ban.rule, 0) + 1
	counts = ", ".join(f"{rule}: {count}" for rule, count in sorted(by_rule.items()))
	preview = "\n".join(_line(ban, REASON_PREVIEW).replace("`", "'") for ban in flagged[:PREVIEW_LINES])
	more = f"\n...and {len(flagged) - PREVIEW_LINES} more in the attached file." if len(flagged) > PREVIEW_LINES else ""
	message = (f"**Ban re-check:** {len(flagged)} of {scanned} shared bans fail the current ban rules ({counts}).\n"
	           f"Nothing has been hidden. Review the list and hide the ones that should not be shared with "
	           f"`/staff banvisibility`.\n```\n{preview}\n```{more}")
	content = "ban_id | rule | server | reason\n" + "\n".join(_line(ban) for ban in flagged) + "\n"
	return message[:2000], content


# ============================================================
async def send(bot) -> list[FlaggedBan] :
	"""Re-checks every approved, visible ban and reports the failures to the DEV channel. Read-only."""
	bans = await asyncio.to_thread(BanTransactions().get_all)
	flagged = await find_flagged(bans)
	logging.info(f"[ban re-check] {len(flagged)}/{len(bans)} shared bans fail the current ban rules.")
	for ban in flagged :
		logging.info(f"[ban re-check] would hide {_line(ban)}")
	if not flagged :
		return flagged

	channel = bot.get_channel(bot.DEV)
	if channel is None :
		logging.warning("Ban re-check report skipped: the DEV channel could not be found.")
		return flagged
	message, content = build_report(flagged, len(bans))
	await channel.send(message, file=discord.File(io.BytesIO(content.encode("utf-8")), "ban-recheck.txt"))
	return flagged
