import logging
import re
from collections.abc import Coroutine
from enum import StrEnum

import discord
from discord.ext import commands

from classes.TermsChecker import TermsChecker
from classes.access import AccessControl
from classes.configdata import ConfigData
from classes.queue import queue
from database.transactions.ServerTransactions import ServerTransactions
from view.v2.EvidenceSubmission import EvidenceUI


class BanCheckerStatus(StrEnum) :
	ERROR = "error"
	HIDE = "hide"
	PROMPT = "prompt"  # this is the default end status
	APPROVE = "approve"
	REVIEW = "review"
	PENDING = "pending"
	SHORT = "short"


class BanChecker() :
	def __init__(self, bot: commands.AutoShardedBot | commands.Bot, ban: discord.BanEntry) :
		self.bot = bot
		self.ban = ban
		self.status: str = BanCheckerStatus.PROMPT
		self.reason = ""

	async def run(self) :
		"""Checks if the ban follows the guidelines of banwatch, and if the ban has damaging claims."""
		await self.auto_hide()
		logging.debug("Hide check: " + self.status)
		await self.perform_action(self.migrated_ban())
		# await self.perform_action(self.check_claims())
		logging.debug("Check: " + self.status)
		await self.perform_action(self.check_bot())
		logging.debug("bot Check: " + self.status)
		await self.perform_action(self.check_staff())
		logging.debug("Staff Check: " + self.status)
		await self.perform_action(self.check_word_count())
		logging.debug("count check: " + self.status)
		await self.perform_action(self.check_flagged_terms(self.ban.reason))
		logging.debug("Final check: " + self.status)
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

	async def check_staff(self) :
		if AccessControl().access_all(self.ban.user.id) :
			self.reason = "Banwatch Staff Member"
			self.status = BanCheckerStatus.REVIEW

	async def check_bot(self) :
		if self.ban.user.bot :
			self.reason = "Member is a bot"
			self.status = BanCheckerStatus.REVIEW

	async def check_word_count(self) :
		word_count = len(self.ban.reason.split(" ")) < 4
		if word_count and ("spam" not in self.ban.reason.lower() or "bot" not in self.ban.reason.lower()) :
			self.reason = "Short ban reason"
			self.status = BanCheckerStatus.SHORT

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
			match result :
				case "review" :
					self.reason = reason
					self.status = BanCheckerStatus.REVIEW

				case "block" :
					self.reason = reason
					self.status = BanCheckerStatus.HIDE

			return None, None
		return None, None

	async def check_pii(self):
		"""This function does its best to detect personally identifiable information such as date of births, phone numbers, addresses, and emails."""
		# This is a very basic check, and can be easily bypassed, but it's better than nothing.
		email_regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
		phone_regex = r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"
		dob_regex = r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b"

		if re.search(email_regex, self.ban.reason) or re.search(phone_regex, self.ban.reason) or re.search(
				dob_regex, self.ban.reason) :
			self.reason = "Ban reason may contain personally identifiable information."
			self.status = BanCheckerStatus.REVIEW

	def get_status(self) -> str :
		"""Returns the status of the ban check."""
		return self.status

	def get_reason(self) -> str :
		"""Returns the reason for the ban check."""
		return self.reason

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
				await Bans().add_ban(self.ban.user.id, guild.id, self.reason, guild.owner.name, hidden=True)
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
					                staff_reason=self.reason)
					queue().add(ui.send_embed(await ConfigData().get_channel(guild)), priority=2)
					# To prevent spamming the approval channel, we hide them instead because this is called during large operations like mass reviewing bans.
					await Bans().add_ban(self.ban.user.id, guild.id, self.ban.reason, guild.owner.name, approved=False,
					                     hidden=True)

					return

				await Bans().add_ban(self.ban.user.id, guild.id, self.ban.reason, guild.owner.name, approved=False)
				return

			case BanCheckerStatus.APPROVE :
				logging.info("Ban has been approved without prompting, adding to database.")
				self.reason = "Ban approved without prompting: " + self.reason
				await Bans().add_ban(self.ban.user.id, guild.id, self.ban.reason, guild.owner.name, approved=True)
				embed = discord.Embed(title=f"{self.ban.user} ({self.ban.user.id}) was banned in {guild}({guild.owner})",
				                      description=f"{self.ban.reason}")
				guild_db = ServerTransactions().get(guild.id)

				embed.set_footer(
					text=f"Server Invite: {guild_db.invite} Staff member: {guild_db.owner} ban ID: {guild.id + self.ban.user.id}. ")
				queue().add(
					Bans().check_guilds(None, bot, guild, self.ban.user, embed, guild.id + self.ban.user.id, silent=True),
					priority=2)
				return

			case BanCheckerStatus.PROMPT :
				if server_only :
					await Bans().add_ban(self.ban.user.id, guild.id, self.ban.reason, guild.owner.name, approved=True)
					embed = discord.Embed(title=f"{self.ban.user} ({self.ban.user.id}) was banned in {guild}({guild.owner})",
					                      description=f"{self.ban.reason}")
					guild_db = ServerTransactions().get(guild.id)

					embed.set_footer(
						text=f"Server Invite: {guild_db.invite} Staff member: {guild_db.owner} ban ID: {guild.id + self.ban.user.id}. ")
					queue().add(

						Bans().check_guilds(None, bot, guild, self.ban.user, embed, guild.id + self.ban.user.id, silent=True),
						priority=2)
					return
				from view.buttons.banoptionbuttons import BanOptionButtons
				view = BanOptionButtons()
				mod_channel = await ConfigData().get_channel(guild)
				if mod_channel is None :
					logging.warning(f"{guild.name}({guild.id}) doesn't have modchannel set, cannot prompt for review.")
				user = self.ban.user
				embed = discord.Embed(title=f"Do you want to share {user}'s ({user.id}) ban with other servers?",
				                      description=f"{self.ban.reason}")
				embed.set_footer(text=f"{guild.id}-{self.ban.user.id}")
				queue().add(mod_channel.send(embed=embed, view=view), priority=2)
				return

			case BanCheckerStatus.SHORT :
				await Bans().add_ban(self.ban.user.id, guild.id, self.ban.reason, guild.owner.name, approved=False)

			case _ :
				logging.info("Ban is pending review, adding to database with pending tag.")
				self.reason = "Ban pending review: " + self.reason
				await Bans().add_ban(self.ban.user.id, guild.id, self.ban.reason, guild.owner.name, approved=False)
