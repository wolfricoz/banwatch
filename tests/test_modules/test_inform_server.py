"""Unit tests for the "Inform Server" button in view/buttons/banapproval.py BanApproval.request_evidence.

Staff pick a preset (or custom) message, the ban is hidden, and the server gets an evidence request
marked as hidden until evidence is provided. Submitting that evidence returns the ban to the queue.
"""
import logging
import unittest
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

from view.buttons.banapproval import BanApproval
from view.multiselect.selectinform import INFORM_PRESETS, SelectInform


class InformServer(unittest.IsolatedAsyncioTestCase) :
	def setUp(self) :
		logging.disable(logging.CRITICAL)
		self.addCleanup(logging.disable, logging.NOTSET)

		self.stack = ExitStack()
		self.addCleanup(self.stack.close)
		p = lambda target, **kw : self.stack.enter_context(patch(f"view.buttons.banapproval.{target}", **kw))
		self.BanTransactions = p("BanTransactions")
		self.SelectInform = p("SelectInform")
		self.EvidenceUI = p("EvidenceUI")
		self.send_modal = p("send_modal", new=AsyncMock(return_value="custom message"))
		self.send_response = p("send_response", new=AsyncMock())
		self.resolve_ban_channel = p("resolve_ban_channel", new=AsyncMock(return_value=MagicMock()))
		self.warn_missing_ban_channel = p("warn_missing_ban_channel", new=AsyncMock())
		self.EvidenceUI.return_value.send_embed = AsyncMock()

		self.ban_entry = MagicMock(approved=False, ban_id=1234, reason="raiding")
		self.BanTransactions.return_value.get.return_value = self.ban_entry

		self.select = self.SelectInform.return_value
		self.select.wait = AsyncMock(return_value=False)
		self.select.interaction = MagicMock()
		self.select.interaction.response.defer = AsyncMock()
		self.select.get_message = MagicMock(return_value=INFORM_PRESETS[1]["message"])

		self.guild = MagicMock()
		self.guild.name = "guild"
		self.denial_channel = MagicMock()
		self.denial_channel.send = AsyncMock()

		# Construct the view without __init__ (discord.ui.View wiring is irrelevant here).
		self.view = BanApproval.__new__(BanApproval)
		self.view.bot = MagicMock()
		self.view.bot.get_channel.return_value = self.denial_channel
		self.view.wait_id = 1234
		self.view.get_ban_data = AsyncMock(return_value=(self.guild, MagicMock(), "raiding"))
		self.view.update_embed = AsyncMock()
		self.view.reply = AsyncMock()
		self.interaction = MagicMock()

	# ============================================================
	async def _press(self) :
		await BanApproval.request_evidence(self.view, self.interaction, MagicMock())

	# ============================================================
	async def test_preset_hides_ban_and_sends_review_request(self) :
		await self._press()
		self.BanTransactions.return_value.update.assert_called_once_with(1234, approved=True, hidden=True)
		self.view.update_embed.assert_awaited_once_with(self.interaction, "inform")
		self.select.interaction.response.defer.assert_awaited_once()
		self.send_modal.assert_not_called()
		_, kwargs = self.EvidenceUI.call_args
		self.assertTrue(kwargs["review"])
		self.assertEqual(kwargs["staff_reason"], INFORM_PRESETS[1]["message"])
		self.EvidenceUI.return_value.send_embed.assert_awaited_once()
		self.denial_channel.send.assert_awaited_once()

	# ============================================================
	async def test_custom_opens_modal_on_select_interaction(self) :
		self.select.get_message.return_value = "custom"
		await self._press()
		self.assertIs(self.send_modal.call_args.args[0], self.select.interaction)
		self.assertEqual(self.EvidenceUI.call_args.kwargs["staff_reason"], "custom message")
		self.BanTransactions.return_value.update.assert_called_once()

	# ============================================================
	async def test_empty_custom_message_changes_nothing(self) :
		self.select.get_message.return_value = "custom"
		self.send_modal.return_value = ""
		await self._press()
		self.BanTransactions.return_value.update.assert_not_called()
		self.EvidenceUI.assert_not_called()

	# ============================================================
	async def test_timeout_changes_nothing(self) :
		self.select.wait.return_value = True
		await self._press()
		self.BanTransactions.return_value.update.assert_not_called()
		self.view.update_embed.assert_not_called()

	# ============================================================
	async def test_already_handled_ban_is_refused(self) :
		self.ban_entry.approved = True
		await self._press()
		self.SelectInform.assert_not_called()
		self.BanTransactions.return_value.update.assert_not_called()

	# ============================================================
	async def test_missing_mod_channel_still_hides_and_warns(self) :
		self.resolve_ban_channel.return_value = None
		await self._press()
		self.BanTransactions.return_value.update.assert_called_once_with(1234, approved=True, hidden=True)
		self.warn_missing_ban_channel.assert_awaited_once()
		self.EvidenceUI.assert_not_called()


class SelectInformMessages(unittest.IsolatedAsyncioTestCase) :
	# Built inside the event loop: discord.ui.View needs a running loop on Python 3.13.
	async def test_get_message_maps_labels_to_messages(self) :
		view = SelectInform()
		self.assertIsNone(view.get_message())
		view.selected = "Custom"
		self.assertEqual(view.get_message(), "custom")
		view.selected = "Proof required (generic)"
		self.assertIn("hidden for the time being", view.get_message())

	# ============================================================
	async def test_presets_fit_discord_limits(self) :
		self.assertLessEqual(len(INFORM_PRESETS), 25)
		for preset in INFORM_PRESETS :
			self.assertLessEqual(len(preset["label"]), 100)
			self.assertLessEqual(len(preset["description"]), 100)


if __name__ == "__main__" :
	unittest.main()
