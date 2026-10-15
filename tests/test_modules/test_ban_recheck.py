"""Unit tests for classes/ban/recheck.py, the weekly re-check of shared bans against the ban rules.

The re-check is report-only: it must find approved, visible bans whose reason fails the current
auto-hide rules, tell staff in the DEV channel, and never change a ban itself.
"""
import logging
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from classes.ban import recheck


def ban_row(ban_id, reason, guild="Guild", verified=False, edited_by=None) :
	row = MagicMock(ban_id=ban_id, gid=ban_id * 10, reason=reason, verified=verified, edited_by=edited_by)
	row.guild.name = guild
	return row


class FindFlagged(unittest.IsolatedAsyncioTestCase) :
	async def test_only_rule_failures_are_flagged(self) :
		rows = [
			ban_row(1, "[silent]Cross-ban from X with ban id: 5 with reason: raiding"),
			ban_row(2, "Raiding the server and spamming slurs"),
			ban_row(3, "N/A."),
			ban_row(4, "raiding"),   # short, but short bans are a review verdict, not an auto-hide
			ban_row(5, "[migrated] legacy", verified=True),
		]
		flagged = await recheck.find_flagged(rows)
		self.assertEqual([(f.ban_id, f.rule) for f in flagged],
		                 [(1, "Cross ban"), (3, "Low Value Ban"), (5, "Migrated ban")])
		self.assertTrue(flagged[2].verified)

	# ============================================================
	async def test_missing_guild_falls_back_to_the_id(self) :
		row = ban_row(7, "test")
		row.guild = None
		flagged = await recheck.find_flagged([row])
		self.assertEqual(flagged[0].guild, "70")


class BuildReport(unittest.TestCase) :
	def _flagged(self, count) :
		return [recheck.FlaggedBan(i, "Guild", "Cross ban" if i % 2 else "Low Value Ban", f"Cross-ban from X `{i}`",
		                           verified=i == 1, edited_by="staffer" if i == 2 else None)
		        for i in range(1, count + 1)]

	# ============================================================
	def test_message_fits_and_says_nothing_was_hidden(self) :
		message, content = recheck.build_report(self._flagged(40), scanned=1000)
		self.assertLessEqual(len(message), 2000)
		self.assertIn("40 of 1000", message)
		self.assertIn("Nothing has been hidden", message)
		self.assertIn("Cross ban: 20", message)
		self.assertIn("Low Value Ban: 20", message)
		self.assertIn("30 more", message)
		# Backticks in a reason would close the code block early.
		self.assertNotIn("`1`", message)

	# ============================================================
	def test_file_lists_every_ban_with_notes(self) :
		_, content = recheck.build_report(self._flagged(40), scanned=1000)
		lines = content.strip().splitlines()
		self.assertEqual(len(lines), 41)   # header + one per ban
		self.assertIn("(verified)", lines[1])
		self.assertIn("(edited by staffer)", lines[2])


class Send(unittest.IsolatedAsyncioTestCase) :
	def setUp(self) :
		logging.disable(logging.CRITICAL)
		self.addCleanup(logging.disable, logging.NOTSET)
		self.bot = MagicMock()
		self.channel = MagicMock()
		self.channel.send = AsyncMock()
		self.bot.get_channel.return_value = self.channel

	# ============================================================
	async def _send(self, rows) :
		with patch("classes.ban.recheck.BanTransactions") as transactions :
			transactions.return_value.get_all.return_value = rows
			flagged = await recheck.send(self.bot)
		return transactions, flagged

	# ============================================================
	async def test_reports_failures_without_changing_bans(self) :
		transactions, flagged = await self._send([ban_row(1, "cross-ban from X"), ban_row(2, "Raiding the server repeatedly")])
		self.assertEqual([f.ban_id for f in flagged], [1])
		self.channel.send.assert_awaited_once()
		self.assertIsNotNone(self.channel.send.await_args.kwargs.get("file"))
		transactions.return_value.update.assert_not_called()

	# ============================================================
	async def test_silent_when_everything_passes(self) :
		_, flagged = await self._send([ban_row(2, "Raiding the server repeatedly")])
		self.assertEqual(flagged, [])
		self.channel.send.assert_not_awaited()

	# ============================================================
	async def test_missing_dev_channel_does_not_raise(self) :
		self.bot.get_channel.return_value = None
		_, flagged = await self._send([ban_row(1, "test")])
		self.assertEqual(len(flagged), 1)


if __name__ == "__main__" :
	unittest.main()
