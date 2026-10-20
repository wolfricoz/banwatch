"""Re-checks the bans the network can see against the current auto-hide rules, for modules.tasks.

BanChecker only judges a ban when it comes in. A ban that got past an older, looser version of the
rules - or past a path that skipped them - stays shared until someone notices it. This finds those
bans and reports them to the stats channel (STATS_CHANNEL env).

The weekly run never hides anything itself: a rule that turns out too broad must not silently pull
hundreds of legitimate bans from the network. Staff read the report and hide them with
/staff hide_flagged (all at once, after a confirmation) or /staff banvisibility (one at a time).
find_flagged(), select() and build_report() take plain data so they can be tested without a bot;
send() posts the result and hide() writes it.
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
	uid: int | None = None

	@property
	def reviewed(self) -> bool :
		"""Staff verified or edited this ban, so it was looked at by a person after it came in."""
		return self.verified or bool(self.edited_by)


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
		flagged.append(FlaggedBan(ban.ban_id, guild, rule, ban.reason or "", bool(ban.verified), ban.edited_by, ban.uid))
	return flagged


# ============================================================
async def scan() -> tuple[list[FlaggedBan], int] :
	"""Re-checks every approved, visible ban. Returns the failures and how many bans were scanned."""
	bans = await asyncio.to_thread(BanTransactions().get_all)
	return await find_flagged(bans), len(bans)


# ============================================================
def select(flagged: list[FlaggedBan], include_reviewed: bool = False) -> tuple[list[FlaggedBan], list[FlaggedBan]] :
	"""Splits the failures into the ones /staff hide_flagged hides and the reviewed ones it leaves alone."""
	if include_reviewed :
		return list(flagged), []
	return [ban for ban in flagged if not ban.reviewed], [ban for ban in flagged if ban.reviewed]


# ============================================================
def hide(flagged: list[FlaggedBan]) -> int :
	"""Hides the given bans, exactly as /staff banvisibility hide:True does. Returns how many changed."""
	hidden = BanTransactions().hide_bulk([ban.ban_id for ban in flagged])
	for ban in flagged :
		if ban.uid is not None :
			BanTransactions().drop_from_cache(ban)
	return hidden


# ============================================================
def count_by_rule(flagged: list[FlaggedBan]) -> str :
	by_rule = {}
	for ban in flagged :
		by_rule[ban.rule] = by_rule.get(ban.rule, 0) + 1
	return ", ".join(f"{rule}: {count}" for rule, count in sorted(by_rule.items()))


# ============================================================
def _line(ban: FlaggedBan, reason_length: int = None) -> str :
	reason = " ".join(ban.reason.split())
	if reason_length and len(reason) > reason_length :
		reason = reason[:reason_length - 1] + "…"
	notes = [note for note, on in (("verified", ban.verified), (f"edited by {ban.edited_by}", ban.edited_by)) if on]
	suffix = f" ({', '.join(notes)})" if notes else ""
	return f"{ban.ban_id} | {ban.rule} | {ban.guild} | {reason}{suffix}"


# ============================================================
def preview(flagged: list[FlaggedBan]) -> str :
	"""The first few failures as a code block, with a pointer to the attached file for the rest."""
	lines = "\n".join(_line(ban, REASON_PREVIEW).replace("`", "'") for ban in flagged[:PREVIEW_LINES])
	more = f"\n...and {len(flagged) - PREVIEW_LINES} more in the attached file." if len(flagged) > PREVIEW_LINES else ""
	return f"```\n{lines}\n```{more}"


# ============================================================
def build_report(flagged: list[FlaggedBan], scanned: int) -> tuple[str, str] :
	"""The stats channel message and the full list for the attached file."""
	reviewed = sum(ban.reviewed for ban in flagged)
	reviewed_note = (f" {reviewed} of them were verified or edited by staff and are only hidden with "
	                 f"`include_reviewed: True`." if reviewed else "")
	message = (f"**Ban re-check:** {len(flagged)} of {scanned} shared bans fail the current ban rules "
	           f"({count_by_rule(flagged)}).\n"
	           f"Nothing has been hidden. Review the list, then hide them all with `/staff hide_flagged` or one at "
	           f"a time with `/staff banvisibility`.{reviewed_note}\n{preview(flagged)}")
	content = "ban_id | rule | server | reason\n" + "\n".join(_line(ban) for ban in flagged) + "\n"
	return message[:2000], content


# ============================================================
async def send(bot) -> list[FlaggedBan] :
	"""Re-checks every approved, visible ban and reports the failures to the stats channel. Read-only."""
	flagged, scanned = await scan()
	logging.info(f"[ban re-check] {len(flagged)}/{scanned} shared bans fail the current ban rules.")
	for ban in flagged :
		logging.info(f"[ban re-check] would hide {_line(ban)}")
	if not flagged :
		return flagged

	channel = bot.get_channel(bot.STATSCHANNEL)
	if channel is None :
		try :
			channel = await bot.fetch_channel(bot.STATSCHANNEL)
		except discord.HTTPException as e :
			logging.warning(f"Ban re-check report skipped: the stats channel {bot.STATSCHANNEL} could not be found: {e}")
			return flagged
	message, content = build_report(flagged, scanned)
	await channel.send(message, file=discord.File(io.BytesIO(content.encode("utf-8")), "ban-recheck.txt"))
	return flagged
