import logging
import re

from collections.abc import Coroutine
from enum import StrEnum

import discord
from discord.ext import commands

from classes.TermsChecker import TermsChecker
from classes.access import AccessControl


class BanCheckerStatus(StrEnum) :
	ERROR = "error"
	HIDE = "hide"
	PROMPT = "prompt"  # this is the default end status
	APPROVE = "approve"
	REVIEW = "review"
	REVIEW_EVIDENCE = "review_evidence"
	PENDING = "pending"
	CANCEL = "cancel"  # if the configuration is incorrect, we don't process the ban.


class BanChecker() :
	def __init__(self, bot: commands.AutoShardedBot, ban: discord.BanEntry, evaluate: bool = True) :
		self.bot = bot
		self.ban = ban
		self.status: str = BanCheckerStatus.PROMPT
		self.reason = ""
		self.evaluate = evaluate

	async def run(self) :
		"""Checks if the ban follows the guidelines of banwatch, and if the ban has damaging claims."""
		await self.auto_hide()
		logging.info("Hide check: " + self.status)
		await self.perform_action(self.migrated_ban())
		# await self.perform_action(self.check_claims())
		logging.info("Check: " + self.status)
		await self.perform_action(self.check_bot())
		logging.info("bot Check: " + self.status)
		await self.perform_action(self.check_staff())
		logging.info("Staff Check: " + self.status)
		await self.perform_action(self.check_word_count())
		logging.info("count check: " + self.status)
		await self.perform_action(self.check_flagged_terms(self.ban.reason))
		logging.info("Final check: " + self.status)
		if not self.evaluate:
			return self
		await self.evaluate_ban()
		return self



	async def perform_action(self, action: Coroutine) :
		"""Performs actions, if the status is incorrect it'll skip the action to prevent overriding the current action."""
		if self.status != BanCheckerStatus.PROMPT :
			action.close()
			return
		await action



	async def auto_hide(self) :
		"""Automatically hides the ban if it meets the criteria for hiding."""
		await self.check_cross_ban()
		await self.perform_action(self.assess_value())



	async def migrated_ban(self) :
		"""Checks if the ban is a migrated ban, and if it is, approves it without prompting."""
		if str(self.ban.reason).lower().startswith('[migrated') :
			logging.info("Migrated ban, not prompting")
			self.status = BanCheckerStatus.APPROVE
			return



	async def check_cross_ban(self) :
		"""Checks if the ban is a cross-ban, and if it is, hides it and adds it to the database."""
		if self.ban.reason is None :
			self.status = BanCheckerStatus.HIDE
			return



		match = re.match(r"Cross-ban from (?P<guild_name>.+?) with ban id: (?P<ban_id>\d+)", str(self.ban.reason))
		if match or str(self.ban.reason).lower() in ['crossban', 'cross-ban'] :
			logging.info("Cross-ban with no additional info, this ban has been hidden")
			self.status = BanCheckerStatus.HIDE
			return



	async def assess_value(self) :
		"""Checks if the ban is worth broadcasting, if the ban has no reason or a reason that doesn't provide valuable information, it'll be hidden."""
		if self.ban.reason is None or self.ban.reason.lower() in ["", "none", "account has no avatar.", "no reason given.",
		                                                          "breaking server rules"] or str(
			self.ban.reason).lower().startswith(
			'[hidden]') :
			logging.info("Hiding ban: Reason doesn't provide valuable information or has hidden tag.")
			self.status = BanCheckerStatus.HIDE
			return


	async def check_staff(self):
		if AccessControl().access_all(self.ban.user.id) :
			self.reason = "Banwatch Staff Member"
			self.status = BanCheckerStatus.REVIEW

	async def check_bot(self):
		if self.ban.user.bot:
			self.reason = "Member is a bot"
			self.status = BanCheckerStatus.REVIEW

	async def check_word_count(self):
		word_count = len(self.ban.reason.split(" ")) < 4
		if word_count and ("spam" not in self.ban.reason.lower() or "bot" not in self.ban.reason.lower()) :
			self.reason = "Short ban reason"
			self.status = BanCheckerStatus.REVIEW

	async def check_flagged_terms(self, target) :
		checks = {
			"reviewCheck"      : TermsChecker("review", target),
			"countReviewCheck" : TermsChecker("countreview", target),
			"blockCheck"       : TermsChecker("block", target),
			"blockReviewCheck" : TermsChecker("countblock", target),
		}
		for key, val in checks.items() :
			val: TermsChecker
			if val.getReviewStatus() == "" :
				continue
			result, reason = val.getResults()
			match result:
				case "review" :
					self.reason = reason
					self.status = BanCheckerStatus.REVIEW

				case "block" :
					self.reason = reason
					self.status = BanCheckerStatus.HIDE

			return None, None
		return None, None

	def get_status(self) -> str :
		"""Returns the status of the ban check."""
		return self.status

	def get_reason(self) -> str :
		"""Returns the reason for the ban check."""
		return self.reason


	async def evaluate_ban(self) :
		"""this function decides the verdict"""
