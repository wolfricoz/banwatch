"""Unit tests for the LIVE ban entry point, listeners/on_member_ban.py.

on_member_ban is a thin orchestrator that delegates all vetting to BanChecker, but it owns
real gating of its own: ignoring the bot/self, deduping, the missing-mod-channel path, the
hidden-server short-circuit, HIDE -> auto-hide vs. everything-else -> review buttons, and the
premium auto-cross-ban. These tests mock BanChecker and the DB/config services so the handler's
control flow is exercised without a live Discord connection.
"""
import logging
import unittest
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

from classes.ban.BanChecker import BanCheckerStatus
from listeners.on_member_ban import BanEvents

HIDE = BanCheckerStatus.HIDE
PROMPT = BanCheckerStatus.PROMPT


class FakeUser :
	def __init__(self, uid=2222, is_bot=False, name="target") :
		self.id = uid
		self.bot = is_bot
		self.name = name

	# ============================================================
	def __str__(self) :
		return self.name


class FakeBan :
	def __init__(self, reason="a normal ban reason", user=None) :
		self.reason = reason
		self.user = user if user is not None else FakeUser()


class OnMemberBan(unittest.IsolatedAsyncioTestCase) :
	def setUp(self) :
		# The handler logs warnings on the ignore/no-channel paths; keep test output clean.
		logging.disable(logging.CRITICAL)
		self.addCleanup(logging.disable, logging.NOTSET)

		self.stack = ExitStack()
		p = lambda target : self.stack.enter_context(patch(f"listeners.on_member_ban.{target}"))
		self.BanTransactions = p("BanTransactions")
		self.ConfigData = p("ConfigData")
		self.ServerTransactions = p("ServerTransactions")
		self.Bans = p("Bans")
		self.AccessControl = p("AccessControl")
		self.BanChecker = p("BanChecker")
		self.queue = p("queue")
		# send_message is an async function, so patch() would auto-create an AsyncMock whose
		# un-awaited coroutine (queue().add(send_message(...))) triggers warnings. Use a plain mock.
		self.send_message = self.stack.enter_context(
			patch("listeners.on_member_ban.send_message", new=MagicMock()))

		# Sensible defaults: no existing ban row, mod channel set, server not hidden, no premium.
		self.BanTransactions.return_value.get.return_value = None
		self.ConfigData.return_value.get_key_or_none.return_value = "modchannel-id"
		self.ConfigData.return_value.get_key.return_value = False
		self.ServerTransactions.return_value.is_hidden.return_value = False
		self.Bans.return_value.add_ban = AsyncMock()

		# BanChecker instance stub: async run/evaluate/prompt, sync status accessor.
		self.checker = self.BanChecker.return_value
		self.checker.short_run = AsyncMock()
		self.checker.evaluate_ban = AsyncMock()
		self.checker.send_review_prompt = AsyncMock()
		self.checker.get_status = MagicMock(return_value=PROMPT)

		# bot / guild / user doubles.
		self.bot = MagicMock()
		self.bot.user = object()
		self.mod_channel = MagicMock()
		self.bot.get_channel = MagicMock(return_value=self.mod_channel)

		self.guild = MagicMock()
		self.guild.id = 999
		self.guild.name = "Guild"
		self.guild.owner = MagicMock()
		self.guild.owner.id = 4242
		self.guild.owner.name = "Owner"
		self.guild.fetch_ban = AsyncMock(return_value=FakeBan())

		self.user = FakeUser()

		# Construct the cog without __init__ (which registers discord views).
		self.cog = BanEvents.__new__(BanEvents)
		self.cog.bot = self.bot
		self.cog.cross_ban = MagicMock()  # avoid creating un-awaited coroutines in the premium path

	# ============================================================
	def tearDown(self) :
		self.stack.close()

	# ============================================================
	async def test_ignores_the_bot_itself(self) :
		self.bot.user = self.user  # user == bot.user
		await self.cog.on_member_ban(self.guild, self.user)
		self.BanChecker.assert_not_called()
		self.Bans.return_value.add_ban.assert_not_awaited()

	# ============================================================
	async def test_ignores_bot_users(self) :
		bot_user = FakeUser(is_bot=True)
		await self.cog.on_member_ban(self.guild, bot_user)
		self.BanChecker.assert_not_called()
		self.Bans.return_value.add_ban.assert_not_awaited()

	# ============================================================
	async def test_missing_mod_channel_dms_owner_and_stops(self) :
		self.bot.get_channel.return_value = None
		await self.cog.on_member_ban(self.guild, self.user)
		self.send_message.assert_called_once()
		self.assertIs(self.send_message.call_args.args[0], self.guild.owner)
		self.BanChecker.assert_not_called()

	# ============================================================
	async def test_hidden_server_records_silently_and_stops(self) :
		self.ServerTransactions.return_value.is_hidden.return_value = True
		await self.cog.on_member_ban(self.guild, self.user)
		self.Bans.return_value.add_ban.assert_awaited_once()
		args = self.Bans.return_value.add_ban.await_args.args
		self.assertEqual(args[0], self.user.id)
		self.assertEqual(args[3], "Unknown")   # staff attribution for hidden-server bans
		self.BanChecker.assert_not_called()    # no vetting / no prompt

	# ============================================================
	async def test_hide_verdict_auto_hides_without_prompt(self) :
		self.checker.get_status.return_value = HIDE
		await self.cog.on_member_ban(self.guild, self.user)
		self.checker.short_run.assert_awaited_once()
		self.checker.evaluate_ban.assert_awaited_once_with(self.guild, server_only=False)
		self.checker.send_review_prompt.assert_not_awaited()

	# ============================================================
	async def test_non_hide_verdict_shows_review_buttons(self) :
		self.checker.get_status.return_value = PROMPT
		await self.cog.on_member_ban(self.guild, self.user)
		self.checker.send_review_prompt.assert_awaited_once_with(self.guild)
		self.checker.evaluate_ban.assert_not_awaited()
		self.cog.cross_ban.assert_not_called()   # premium off by default

	# ============================================================
	async def test_premium_cross_ban_mirrors_to_owner_servers(self) :
		self.checker.get_status.return_value = PROMPT
		self.ConfigData.return_value.get_key.return_value = True
		self.AccessControl.return_value.is_premium.return_value = True
		# NOTE: `name=` is a reserved MagicMock kwarg, so set .name explicitly.
		server_a, server_b = MagicMock(), MagicMock()
		server_a.id, server_a.name = 1, "A"
		server_b.id, server_b.name = 2, "B"
		self.ServerTransactions.return_value.get_owners_servers.return_value = [server_a, server_b]

		await self.cog.on_member_ban(self.guild, self.user)

		self.assertEqual(self.cog.cross_ban.call_count, 2)
		# The mod channel is notified, and the review prompt is still shown for a shareable ban.
		self.send_message.assert_called()
		self.checker.send_review_prompt.assert_awaited_once_with(self.guild)


if __name__ == "__main__" :
	unittest.main()
