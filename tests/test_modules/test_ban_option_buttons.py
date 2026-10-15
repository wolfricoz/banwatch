"""Unit tests for the verdict routing in view/buttons/banoptionbuttons.py BanOptionButtons.process.

The live path (listeners/on_member_ban.py) only runs BanChecker.short_run() and leaves the full check
to these buttons. process() then routes on the full verdict: HIDE is stored hidden, REVIEW and SHORT
go to the staff queue unapproved, and only PROMPT is approved and broadcast. SHORT used to fall
through to the broadcast branch, which is how short reasons reached the network.
"""
import logging
import unittest
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

from classes.ban.BanChecker import BanCheckerStatus
from view.buttons.banoptionbuttons import BanOptionButtons


class FakeUser :
	def __init__(self, uid=2222, name="target") :
		self.id = uid
		self.name = name
		self.bot = False
		self.mention = f"<@{uid}>"

	# ============================================================
	def __str__(self) :
		return self.name


class FakeBan :
	def __init__(self, reason) :
		self.reason = reason
		self.user = FakeUser()


class ProcessRouting(unittest.IsolatedAsyncioTestCase) :
	def setUp(self) :
		logging.disable(logging.CRITICAL)
		self.addCleanup(logging.disable, logging.NOTSET)

		self.stack = ExitStack()
		self.addCleanup(self.stack.close)
		p = lambda target, **kw : self.stack.enter_context(patch(f"view.buttons.banoptionbuttons.{target}", **kw))
		self.Bans = p("Bans")
		self.queue = p("queue")
		self.BanChecker = p("BanChecker")
		p("ServerTransactions")
		p("ProofTransactions").return_value.count.return_value = 0
		p("BanApproval")
		p("send_message", new=MagicMock())
		p("send_response", new=AsyncMock())
		p("inform_user", new=MagicMock())
		p("os")

		self.checker = self.BanChecker.return_value
		self.checker.run = AsyncMock()
		self.checker.get_reason = MagicMock(return_value="Short ban reason")

		self.guild = MagicMock()
		self.guild.id = 999
		self.user = FakeUser()

		# Construct the view without __init__ (discord.ui.View wiring is irrelevant here).
		self.view = BanOptionButtons.__new__(BanOptionButtons)
		self.view.wait_id = None
		self.view.get_staff_member = AsyncMock(return_value=MagicMock())
		self.view.sendDeniedEmbed = AsyncMock()
		self.view.status = MagicMock()
		self.view.provide_proof = MagicMock()
		self.interaction = MagicMock()
		self.interaction.message.delete = AsyncMock()

	# ============================================================
	async def _process(self, status, reason="raiding", **kwargs) :
		self.checker.get_status = MagicMock(return_value=status)
		self.view.get_data = AsyncMock(return_value=(self.guild, self.user, FakeBan(reason)))
		await self.view.process(self.interaction, **kwargs)
		return self.Bans.return_value

	# ============================================================
	async def test_short_goes_to_review_not_broadcast(self) :
		for silent in (False, True) :
			with self.subTest(silent=silent) :
				self.Bans.reset_mock()
				bans = await self._process(BanCheckerStatus.SHORT, silent=silent)
				_, kwargs = bans.add_ban.call_args
				self.assertFalse(kwargs.get("approved"))
				bans.check_guilds.assert_not_called()
				self.view.status.assert_called_with(
					self.interaction.client, self.guild, self.user, "waiting_approval", "raiding",
					word="Short ban reason", message=self.interaction.message, silent=silent)

	# ============================================================
	async def test_review_goes_to_review(self) :
		bans = await self._process(BanCheckerStatus.REVIEW)
		self.assertFalse(bans.add_ban.call_args.kwargs.get("approved"))
		bans.check_guilds.assert_not_called()

	# ============================================================
	async def test_prompt_is_approved_and_broadcast(self) :
		bans = await self._process(BanCheckerStatus.PROMPT, reason="raiding the whole server repeatedly")
		self.assertTrue(bans.add_ban.call_args.kwargs.get("approved"))
		bans.check_guilds.assert_called_once()

	# ============================================================
	async def test_hide_is_stored_hidden_even_without_a_reason(self) :
		# None + str used to raise here, so the ban was never recorded at all.
		bans = await self._process(BanCheckerStatus.HIDE, reason=None)
		args, kwargs = bans.add_ban.call_args
		self.assertTrue(kwargs.get("hidden"))
		self.assertIn("HIDDEN DUE TO BLOCKLIST", args[2])
		bans.check_guilds.assert_not_called()


if __name__ == "__main__" :
	unittest.main()
