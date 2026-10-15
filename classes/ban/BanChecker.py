import logging
import re
import unicodedata
from collections.abc import Coroutine
from enum import StrEnum
from types import SimpleNamespace

import discord
from discord import Forbidden
from discord.ext import commands

from classes.TermsChecker import TermsChecker
from classes.access import AccessControl
from classes.ban.ban_channel import UNREACHABLE, UNSET, resolve_ban_channel, warn_missing_ban_channel
from classes.configdata import ConfigData
from classes.queue import queue
from data.config.mappings import Channels
from database.transactions.ServerTransactions import ServerTransactions

from resources.bans.BanCheckVariables import BAN_STARTS_WITH, IGNORED_REASONS, REASON_TAGS
from view.v2.EvidenceSubmission import EvidenceUI

# Characters that render as nothing (soft hyphen, zero-width spaces/joiners, BOM). Copy-pasted reasons
# carry them, and "n\u200b/a" looks exactly like "n/a" while comparing unequal.
_INVISIBLE = dict.fromkeys(map(ord, "\u00ad\u200b\u200c\u200d\u2060\ufeff"), None)
# Hyphen lookalikes (hyphen, non-breaking hyphen, figure/en/em dash, minus) that NFKC leaves alone.
_DASHES = re.compile("[\u2010-\u2015\u2212]")
# A leading "[silent]" / "(hidden)" tag; /ban and /reban prepend them with no space after.
_LEADING_TAG = re.compile(r"[\[(]\s*(" + "|".join(map(re.escape, REASON_TAGS)) + r")\s*[\])]\s*")
# Stripped from both ends before comparing against IGNORED_REASONS, so "None.", "(n/a)" and "`test`" match.
_EDGE_PUNCTUATION = " .,!?;:'\"`*_~()[]{}<>-"
# "cross-ban from X", "Cross banned from X", "crossban: X", "[Cross-ban] from X", "cross-ban - X" or just
# "cross-ban". Anchored at the start, so a reason that merely mentions a cross-ban is left alone.
_CROSS_BAN = re.compile(r"cross[\s_-]*ban(?:ned)?[\])}>\"'`*_]*(?:\s+from\s+\S|\s*[:|-]\s*\S|$)")


class BanCheckerStatus(StrEnum) :
	ERROR = "error"
	HIDE = "hide"
	PROMPT = "prompt"  # this is the default end status
	APPROVE = "approve"
	REVIEW = "review"
	PENDING = "pending"
	SHORT = "short"


# BanChecker is the single source of truth for ban vetting. All paths route through it:
#  - live bans:  listeners/on_member_ban.py  (run() + evaluate_ban(server_only=False))
#  - mass review: classes/bans.py, modules/Staff.py, view/buttons/banoptionbuttons.py
#  - ban rows:   auto_hide_verdict() for hidden servers, the bulk approval and the periodic re-check
#                (classes/ban/recheck.py)
# Every rule judges split_reason(), never the raw reason, so case, unicode and [silent]/[hidden]
# tags can't make one rule see a different reason than another.
# Keep the rules (cross-ban, low-value, migrated, flagged terms, PII, short) here only - do not
# reintroduce a copy in the listeners, or the two will drift and a ban can be hidden by one path
# and broadcast by another.
class BanChecker() :
	def __init__(self, bot: commands.AutoShardedBot | commands.Bot, ban: discord.BanEntry) :
		self.bot = bot
		self.ban = ban
		self.status: str = BanCheckerStatus.PROMPT
		self.reason = ""

	# ============================================================
	async def run(self) :
		"""Checks if the ban follows the guidelines of banwatch, and if the ban has damaging claims."""
		await self.auto_hide()
		logging.info("[BanChecker] Hide check: " + self.status)

		await self.perform_action(self.check_flagged_terms(self.ban.reason))
		logging.info("[BanChecker] Final check: " + self.status)

		await self.perform_action(self.migrated_ban())
		logging.info("[BanChecker] Check: " + self.status)

		await self.perform_action(self.check_bot())
		logging.info("[BanChecker] bot Check: " + self.status)

		await self.perform_action(self.check_staff())
		logging.info("[BanChecker] Staff Check: " + self.status)

		await self.perform_action(self.check_word_count())
		logging.info("[BanChecker] count check: " + self.status)

		await self.perform_action(self.check_pii())
		logging.info("[BanChecker] PII check: " + self.status)

		# await self.perform_action(self.check_ascii_alphanumeric())
		# logging.info("[BanChecker] Alphanumeric check: " + self.status)

		return self

	# ============================================================
	async def short_run(self) :
		"""Lightweight PRE-CHECK for the live on-ban event. Runs ONLY the cheap, string-only auto-hide
		rules - cross-ban, low-value and migrated - so we can decide 'auto-hide vs show buttons'
		without the expensive parts of the full check (flagged-term DB lookups, staff/PII scans).
		Leaves status at PROMPT unless the ban is a definitive auto-hide (HIDE). The full run() is
		still performed later by the review buttons, which do the REAL check."""
		await self.auto_hide()
		logging.info("[BanChecker] short-run hide check: " + self.status)

		await self.perform_action(self.migrated_ban())
		logging.info("[BanChecker] short-run migrated check: " + self.status)

		return self

	# ============================================================
	@staticmethod
	def normalise_reason(reason) -> str :
		"""The form every rule compares against: NFKC (full-width and styled letters become plain
		ASCII), invisible characters removed, dash lookalikes turned into "-", case-folded and with
		whitespace collapsed. Without this, a full-width "cross-ban", "Cross\u2013ban" (en dash) or "n\u200b/a"
		all read as the real thing to a moderator but slip past the rules."""
		text = unicodedata.normalize("NFKC", str(reason or ""))
		text = _DASHES.sub("-", text.translate(_INVISIBLE))
		return " ".join(text.casefold().split())

	# ============================================================
	@classmethod
	def split_reason(cls, reason) -> tuple[set[str], str] :
		"""Normalises the reason and peels the leading [silent]/[hidden] tags off it. Returns the tags
		found and the rest of the reason, which is what the rules judge."""
		text = cls.normalise_reason(reason)
		tags = set()
		while match := _LEADING_TAG.match(text) :
			tags.add(match.group(1))
			text = text[match.end():]
		return tags, text

	# ============================================================
	@classmethod
	async def auto_hide_verdict(cls, reason) -> str | None :
		"""Runs the string-only auto-hide rules (the ones short_run() runs) on a bare reason, for
		callers that hold a ban ROW rather than a discord.BanEntry: the bulk approval and the
		periodic re-check. Returns why the reason should be hidden ("Cross ban", "Low Value Ban",
		"Migrated ban"), or None when it passes."""
		checker = cls(None, SimpleNamespace(reason=reason, user=None))
		await checker.short_run()
		return checker.reason if checker.status == BanCheckerStatus.HIDE else None

	# ============================================================
	async def perform_action(self, action: Coroutine) :
		"""Performs actions, if the status is incorrect it'll skip the action to prevent overriding the current action."""
		if self.status != BanCheckerStatus.PROMPT :
			action.close()
			return
		await action

	# ============================================================
	async def auto_hide(self) :
		"""Automatically hides the ban if it meets the criteria for hiding."""
		await self.check_cross_ban()
		await self.perform_action(self.assess_value())

	# ============================================================
	async def migrated_ban(self) :
		"""Checks if the ban is a migrated ban, and if it is, approves it without prompting."""
		_, body = self.split_reason(self.ban.reason)
		if body.startswith('[migrated') :
			logging.info("Migrated ban, not prompting")
			self.status = BanCheckerStatus.HIDE
			self.reason = "Migrated ban"
			return

	# ============================================================
	async def check_cross_ban(self) :
		"""Checks if the ban is a cross-ban, and if it is, hides it and adds it to the database."""
		# A ban is a cross-ban if its reason starts with "cross-ban from <server>", in any of the
		# formats used across the codebase:
		#   - "Cross-ban from <server> with ban id: <n>"                    (auto: on_member_ban / selectban / baninform)
		#   - "Cross-ban from <server> with ban id: <n> with reason: ..."   (auto, with appended reason)
		#   - "Cross-ban from <server>: <reason>"                           (manual, per view/buttons/lookup.py:58)
		#   - "[silent]Cross-ban from <server>: <reason>"                   (/ban and /reban with a ban type)
		# The reason is normalised first (case, unicode, dashes, [silent]/[hidden] tags); the match
		# tolerates "cross ban"/"crossban"/"cross-banned" and a bracketed "[Cross-ban]", and does NOT
		# require the "with ban id" suffix. See _CROSS_BAN.
		_, body = self.split_reason(self.ban.reason)
		if _CROSS_BAN.match(body.strip(_EDGE_PUNCTUATION)) :
			logging.info("Cross-ban detected, this ban has been hidden")
			self.status = BanCheckerStatus.HIDE
			self.reason = "Cross ban"
			return

	# ============================================================
	async def assess_value(self) :
		"""Checks if the ban is worth broadcasting, if the ban has no reason or a reason that doesn't provide valuable information, it'll be hidden."""
		tags, body = self.split_reason(self.ban.reason)
		core = body.strip(_EDGE_PUNCTUATION)
		if (
				"hidden" in tags
				or not core
				or core in IGNORED_REASONS
				or body.startswith(BAN_STARTS_WITH)
				or core.startswith(BAN_STARTS_WITH)
				or "no reason specified" in core
		) :
			logging.info("Hiding ban: Reason doesn't provide valuable information or has hidden tag.")
			self.status = BanCheckerStatus.HIDE
			self.reason = "Low Value Ban"
			return

	# ============================================================
	async def check_staff(self) :
		if AccessControl().access_all(self.ban.user.id) :
			self.reason = "Banwatch Staff Member"
			self.status = BanCheckerStatus.REVIEW

	# ============================================================
	async def check_bot(self) :
		if self.ban.user.bot :
			self.reason = "Member is a bot"
			self.status = BanCheckerStatus.REVIEW

	# ============================================================
	async def check_word_count(self) :
		if self.ban.reason is None :
			self.reason = "Short ban reason"
			self.status = BanCheckerStatus.SHORT
			return

		# Counted without the [silent]/[hidden] tag, or "[silent] ban evasion alt" would pass as 4 words.
		_, body = self.split_reason(self.ban.reason)
		is_short = len(body.split()) < 4

		# Checks if its a common reason such as spam or bot.
		mentions_spam_or_bot = re.search(r"\b(?:spam|bot)\b", body) is not None
		if is_short and not mentions_spam_or_bot :
			self.reason = "Short ban reason"
			self.status = BanCheckerStatus.SHORT

	# ============================================================
	@staticmethod
	def _normalise_found(found) -> str :
		"""getResults() returns the raw `found` matches (a list, possibly of regex-group tuples).
		Flatten to a readable, de-duplicated comma-separated string so every downstream path (which
		concatenates self.reason with a str) always receives a str."""
		if isinstance(found, str) :
			return found
		terms = []
		for item in found or () :
			# re.findall with capture groups yields tuples; flatten and drop empty groups.
			parts = item if isinstance(item, tuple) else (item,)
			for part in parts :
				text = str(part).strip()
				if text and text not in terms :
					terms.append(text)
		return ", ".join(terms)

	# ============================================================
	async def check_flagged_terms(self, target) :
		# "block" (HIDE) always outranks "review" (REVIEW). We therefore return immediately on the
		# first block, and only fall back to a review verdict if no block was found - so a later
		# review check can never downgrade a block. self.reason is normalised to a str here so the
		# HIDE/REVIEW branches of evaluate_ban never try to concatenate a list.
		checks = {
			"reviewCheck"      : TermsChecker("review", target),
			"countReviewCheck" : TermsChecker("countreview", target),
			"blockCheck"       : TermsChecker("block", target),
			"blockReviewCheck" : TermsChecker("countblock", target),
		}
		review_reason: str | None = None
		for key, val in checks.items() :
			val: TermsChecker
			if val.getReviewStatus() == "" :
				continue
			result, found = val.getResults()
			reason_text = self._normalise_found(found)
			if result == "block" :
				self.reason = reason_text
				self.status = BanCheckerStatus.HIDE
				return None, None
			if result == "review" and review_reason is None :
				review_reason = reason_text

		if review_reason is not None :
			self.reason = review_reason
			self.status = BanCheckerStatus.REVIEW
		return None, None

	# ============================================================
	async def check_pii(self) :
		"""This function does its best to detect personally identifiable information such as date of births, phone numbers, addresses, and emails."""
		# This is a very basic check, and can be easily bypassed, but it's better than nothing.
		email_regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
		phone_regex = r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"
		dob_regex = r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b"
		if self.ban.reason is None :
			return

		if re.search(email_regex, self.ban.reason) or re.search(phone_regex, self.ban.reason) or re.search(
				dob_regex, self.ban.reason) :
			self.reason = "Ban reason may contain personally identifiable information."
			self.status = BanCheckerStatus.REVIEW

	# ============================================================
	async def check_ascii_alphanumeric(self) :
		# Ensure we have a string to work with
		return


		reason_str = str(self.ban.reason or "")

		# This regex looks for anything that IS NOT:
		# a-z, A-Z, 0-9, whitespace (\s), or the characters . , ! ? - _ ( )
		if re.search(r'[^\x20-\x7E]', reason_str) :
			self.reason = "Ban reason contains unsupported special characters or emojis."
			self.status = BanCheckerStatus.REVIEW

	# ============================================================
	def get_status(self) -> str :
		"""Returns the status of the ban check."""
		logging.info(f"returning status for {self.ban.user} with reason: {self.ban.reason}, current status: {self.status}")
		return self.status

	# ============================================================
	def get_reason(self) -> str :
		"""Returns the reason for the ban check."""
		logging.info(f"returning reason for {self.ban.user} with reason: {self.ban.reason}, current status: {self.reason}")
		return self.reason

	# ============================================================
	async def send_review_prompt(self, guild) :
		"""Queues the 'share this ban?' prompt (embed + action buttons) to the guild's mod channel.
		This is the interactive path: the buttons run the full check again when a moderator acts, so
		callers use this for any ban that is not a definitive auto-hide.

		If there is no usable mod channel, the prompt cannot be shown - the embed names the banned
		user and quotes the ban reason, so it must never be redirected to some other channel. We warn
		the server instead (see classes/ban/ban_channel.py), in a random channel we can post in, with
		no ban details in it."""
		from view.buttons.banoptionbuttons import BanOptionButtons
		configured = ConfigData().get_key_or_none(guild.id, Channels.MOD_CHANNEL)
		mod_channel = await resolve_ban_channel(guild)
		if mod_channel is None :
			await warn_missing_ban_channel(
				guild, problem=UNSET if not configured else UNREACHABLE, source="ban")
			return
		user = self.ban.user
		embed = discord.Embed(title=f"Do you want to share {user}'s ({user.id}) ban with other servers?",
		                      description=f"{self.ban.reason}")
		embed.set_footer(text=f"{guild.id}-{self.ban.user.id}")
		queue().add(self._deliver_review_prompt(guild, mod_channel, embed, BanOptionButtons()), priority=2)

	# ============================================================
	async def _deliver_review_prompt(self, guild, mod_channel, embed, view) :
		"""Send the prompt, and warn elsewhere if the send fails after all.

		resolve_ban_channel checks the cached permissions, but only the send itself proves the
		channel is usable - permissions can change between the two, and the queue would otherwise
		swallow the failure and leave the server thinking the ban was handled."""
		try :
			await mod_channel.send(embed=embed, view=view)
		except (discord.Forbidden, discord.HTTPException) as e :
			logging.warning(
				f"Could not deliver the ban review prompt to #{mod_channel.name} in {guild.name}({guild.id}): {e}")
			await warn_missing_ban_channel(guild, problem=UNREACHABLE, source="ban", exclude=mod_channel)

	# ============================================================
	async def evaluate_ban(self, guild, server_only=False) :
		"""this function decides the verdict"""
		logging.info(
			f"Evaluating ban for {self.ban.user} in {guild.name} with reason: {self.ban.reason}, current status: {self.status}")
		bot = self.bot

		from classes.bans import Bans
		match self.status :
			case BanCheckerStatus.HIDE :
				logging.info("Ban has been hidden, adding to database with hidden tag.")
				self.reason = "Ban hidden: " + self.reason
				await Bans().add_ban(self.ban.user.id, guild.id, self.reason, guild.owner.name, hidden=True, status=self.status)
				return

			case BanCheckerStatus.REVIEW :
				logging.info("Ban has been marked for review, adding to database with review tag.")
				if isinstance(self.reason, list) :
					self.reason = ", ".join(self.reason)

				self.reason = "Ban marked for review: " + self.reason
				if server_only and len(self.ban.reason.split(" ")) > 4 :
					logging.info("ban marked for review")
					self.reason = "Ban marked for review and has been hidden until evidence has been provided: " + self.reason
					ui = EvidenceUI(self.ban.user, guild, self.ban.user.id + guild.id, reason=self.ban.reason,
					                staff_reason=self.reason, review=True)
					# Like the review prompt, this embed carries ban details, so it goes to the mod
					# channel or nowhere. The ban is still recorded below either way.
					evidence_channel = await resolve_ban_channel(guild)
					if evidence_channel is None :
						await warn_missing_ban_channel(guild, problem=UNSET, source="evidence")
					else :
						queue().add(ui.send_embed(evidence_channel), priority=2)
					# To prevent spamming the approval channel, we hide them instead because this is called during large operations like mass reviewing bans.
					await Bans().add_ban(self.ban.user.id, guild.id, self.ban.reason, guild.owner.name, approved=False,
					                     hidden=True, status=self.status)

					return

				await Bans().add_ban(self.ban.user.id, guild.id, self.ban.reason, guild.owner.name, approved=False,
				                     status=self.status)
				return

			case BanCheckerStatus.APPROVE :
				self.reason = "Ban approved without prompting: " + self.reason
				ban = await Bans().add_ban(self.ban.user.id, guild.id, self.ban.reason, guild.owner.name, approved=True,
				                           status=self.status)
				if not ban :
					return
				embed = discord.Embed(title=f"{self.ban.user} ({self.ban.user.id}) was banned in {guild}({guild.owner})",
				                      description=f"{ban.reason}")
				guild_db = ServerTransactions().get(guild.id)

				embed.set_footer(
					text=f"Server Invite: {guild_db.invite} Staff member: {guild_db.owner} ban ID: {guild.id + self.ban.user.id}. ")
				queue().add(
					Bans().check_guilds(None, bot, guild, self.ban.user, embed, guild.id + self.ban.user.id, silent=True),
					priority=0)
				return

			case BanCheckerStatus.PROMPT :
				if server_only :
					ban = await Bans().add_ban(self.ban.user.id, guild.id, self.ban.reason, guild.owner.name, approved=True,
					                           status=self.status)
					if not ban:
						return

					embed = discord.Embed(title=f"{self.ban.user} ({self.ban.user.id}) was banned in {guild}({guild.owner})",
					                      description=f"{ban.reason}")
					guild_db = ServerTransactions().get(guild.id)

					embed.set_footer(
						text=f"Server Invite: {guild_db.invite} Staff member: {guild_db.owner} ban ID: {guild.id + self.ban.user.id}. ")
					queue().add(

						Bans().check_guilds(None, bot, guild, self.ban.user, embed, guild.id + self.ban.user.id, silent=True),
						priority=0)
					return
				await self.send_review_prompt(guild)
				return

			case BanCheckerStatus.SHORT :
				await Bans().add_ban(self.ban.user.id, guild.id, self.ban.reason, guild.owner.name, approved=False,
				                     status=self.status)

			case _ :
				logging.info("Ban is pending review, adding to database with pending tag.")
				self.reason = "Ban pending review: " + self.reason
				await Bans().add_ban(self.ban.user.id, guild.id, self.ban.reason, guild.owner.name, approved=False,
				                     status=self.status)
