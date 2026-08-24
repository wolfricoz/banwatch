"""Unit tests for Bans.revoke_bans, classes/bans.py.

Revoking is two separate jobs sharing one entry point: pulling the broadcast messages (every
caller wants this) and retracting the verdict (only a staff revoke wants it). The verdict reset
must clear approved, verified AND hidden and put the ban back in front of staff, exactly once,
even when there are no broadcast messages left to pull - and it must NOT fire for the hide
buttons and the unban listener, which call in with staff=False right after hiding a ban.
"""
import logging
import unittest
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

from classes.bans import Bans


class FakeBanMessage :
	def __init__(self, message_id, server_id=555) :
		self.message_id = message_id
		self.server_id = server_id


class RevokeBans(unittest.IsolatedAsyncioTestCase) :
	BAN_ID = 1234

	def setUp(self) :
		logging.disable(logging.CRITICAL)
		self.addCleanup(logging.disable, logging.NOTSET)

		self.stack = ExitStack()
		self.addCleanup(self.stack.close)
		p = lambda target : self.stack.enter_context(patch(f"classes.bans.{target}"))
		self.BanTransactions = p("BanTransactions")
		self.BanMessageTransactions = p("BanMessageTransactions")
		self.ConfigData = p("ConfigData")
		self.queue = p("queue")
		# delete_message is a coroutine function handed to queue().add(); with the queue mocked it
		# would never be awaited, so swap it for a plain mock.
		self.stack.enter_context(patch.object(Bans, "delete_message", new=MagicMock()))
		# revoke_bans imports this lazily from classes.tasks, so patch it at its source.
		self.queue_for_review = self.stack.enter_context(
			patch("classes.tasks.queue_ban_for_review", new=AsyncMock(return_value=True)))

		self.ConfigData.return_value.get_channel = AsyncMock(return_value=MagicMock())
		self.BanTransactions.return_value.update.return_value = MagicMock(ban_id=self.BAN_ID)
		self.bot = MagicMock()

	# ============================================================
	def set_ban_messages(self, *message_ids) :
		self.BanMessageTransactions.return_value.get_by_ban_id.return_value = [
			FakeBanMessage(mid) for mid in message_ids]

	# ============================================================
	def assert_reset_to_pending(self) :
		self.BanTransactions.return_value.update.assert_called_once_with(
			self.BAN_ID, approved=False, verified=False, hidden=False)
		self.queue_for_review.assert_awaited_once()

	# ============================================================
	async def test_staff_revoke_resets_every_flag_and_requeues(self) :
		self.set_ban_messages(1, 2)
		await Bans().revoke_bans(self.bot, self.BAN_ID, "reason", staff=True)
		self.assert_reset_to_pending()

	# ============================================================
	async def test_staff_revoke_without_ban_messages_still_requeues(self) :
		# The reset used to live inside the message loop, so a ban whose broadcasts were already
		# gone kept its approved flag and never came back to the queue.
		self.set_ban_messages()
		await Bans().revoke_bans(self.bot, self.BAN_ID, "reason", staff=True)
		self.assert_reset_to_pending()

	# ============================================================
	async def test_staff_revoke_with_unreachable_mod_channels_still_requeues(self) :
		self.set_ban_messages(1, 2)
		self.ConfigData.return_value.get_channel = AsyncMock(return_value=None)
		await Bans().revoke_bans(self.bot, self.BAN_ID, "reason", staff=True)
		self.assert_reset_to_pending()

	# ============================================================
	async def test_staff_revoke_accepts_a_string_ban_id(self) :
		self.set_ban_messages(1)
		await Bans().revoke_bans(self.bot, str(self.BAN_ID), "reason", staff=True)
		self.assert_reset_to_pending()

	# ============================================================
	async def test_non_staff_revoke_leaves_the_ban_alone(self) :
		# The hide buttons revoke the broadcast right after setting hidden=True; resetting the
		# flags here would immediately un-hide the ban they just hid.
		self.set_ban_messages(1)
		await Bans().revoke_bans(self.bot, self.BAN_ID, "reason")
		self.BanTransactions.return_value.update.assert_not_called()
		self.queue_for_review.assert_not_awaited()

	# ============================================================
	async def test_missing_ban_is_not_queued_for_review(self) :
		self.set_ban_messages(1)
		self.BanTransactions.return_value.update.return_value = False
		self.assertFalse(await Bans().return_to_queue(self.bot, self.BAN_ID))
		self.queue_for_review.assert_not_awaited()


if __name__ == "__main__" :
	unittest.main()
