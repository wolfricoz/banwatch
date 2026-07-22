import logging
import re
from collections.abc import Coroutine
from enum import StrEnum

import discord
from discord import Forbidden
from discord.ext import commands

from classes.TermsChecker import TermsChecker
from classes.access import AccessControl
from classes.configdata import ConfigData
from classes.queue import queue
from database.transactions.ServerTransactions import ServerTransactions

from resources.bans.BanCheckVariables import BAN_STARTS_WITH, IGNORED_REASONS
from view.v2.EvidenceSubmission import EvidenceUI


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
		if str(self.ban.reason).lower().startswith('[migrated') :
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
		# Match is case-insensitive, tolerates "cross ban"/"crossban", and does NOT require the
		# "with ban id" suffix. Anchored at the start so it won't false-positive on reasons that merely
		# mention a cross-ban. Keep this identical to listeners/on_member_ban.py.
		reason = str(self.ban.reason).strip()
		is_cross_ban = (
				re.match(r"cross[-\s]?ban from\s+\S", reason, re.IGNORECASE) is not None
				or reason.lower() in ("crossban", "cross-ban", "cross ban")
		)
		if is_cross_ban :
			logging.info("Cross-ban detected, this ban has been hidden")
			self.status = BanCheckerStatus.HIDE
			self.reason = "Cross ban"
			return

	# ============================================================
	async def assess_value(self) :
		"""Checks if the ban is worth broadcasting, if the ban has no reason or a reason that doesn't provide valuable information, it'll be hidden."""
		raw_reason = str(self.ban.reason or "").lower().strip()
		ignored_reasons = IGNORED_REASONS
		if (
				not raw_reason
				or raw_reason in ignored_reasons
				or raw_reason.startswith(BAN_STARTS_WITH)
				or "no reason specified" in raw_reason
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

		is_short = len(self.ban.reason.split()) < 4

		# Checks if its a common reason such as spam or bot.
		mentions_spam_or_bot = re.search(r"\b(?:spam|bot)\b", self.ban.reason.lower()) is not None
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
		callers use this for any ban that is not a definitive auto-hide. Does nothing if there is no
		mod channel configured."""
		from view.buttons.banoptionbuttons import BanOptionButtons
		mod_channel = await ConfigData().get_channel(guild)
		if mod_channel is None :
			try :
				await guild.owner.send(
					"No moderation channel set, please setup your moderation channel using the /Config commands. Your ban has not been broadcasted but has been recorded")
			except discord.Forbidden:
				for channel in guild.channels :
					try :
						await channel.send(
							"No moderation channel set, please setup your moderation channel using the /Config commands. Your ban has not been broadcasted but has been recorded")
					except discord.NotFound or discord.Forbidden :
						continue
					return
			return
		user = self.ban.user
		embed = discord.Embed(title=f"Do you want to share {user}'s ({user.id}) ban with other servers?",
		                      description=f"{self.ban.reason}")
		embed.set_footer(text=f"{guild.id}-{self.ban.user.id}")
		queue().add(mod_channel.send(embed=embed, view=BanOptionButtons()), priority=2)

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
					queue().add(ui.send_embed(await ConfigData().get_channel(guild)), priority=2)
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
