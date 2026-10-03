import asyncio
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from classes.support import quickleaves
from classes.support.logreader import read_records

GUILD = 612345678901234567
OTHER = 798765432109876543


def _log_lines(now: datetime) -> list[str] :
	stamp = lambda delta : (now - delta).strftime("%Y-%m-%d %H:%M:%S")
	return [
		f"{stamp(timedelta(days=30))},001:root:INFO: Test({GUILD}): a(1) issued appcommand: `old` with arguments: {{}}\n",
		f"{stamp(timedelta(hours=3))},001:root:INFO: Test joined, refreshing ban list\n",
		f"{stamp(timedelta(hours=3))},002:root:INFO: Server Info: Test({GUILD}) has 40 members\n",
		f"{stamp(timedelta(hours=2))},001:root:INFO: Test({GUILD}): a(1) issued appcommand: `lookup` with arguments: {{}}\n",
		f"{stamp(timedelta(hours=2))},002:root:INFO: Test({GUILD}): a(1) issued appcommand: `lookup` with arguments: {{}}\n",
		f"{stamp(timedelta(hours=1))},001:root:INFO: Test({GUILD}): a(1) issued appcommand: `checkall` with arguments: {{}}\n",
		f"{stamp(timedelta(hours=1))},002:root:INFO: Other({OTHER}): b(2) issued appcommand: `lookup` with arguments: {{}}\n",
		f"{stamp(timedelta(minutes=30))},001:root:WARNING: \n",
		f"Test {GUILD} config with arguments {{}}: Traceback (most recent call last):\n",
		"  KeyError: 'modchannel'\n",
		f"{stamp(timedelta(minutes=10))},001:root:INFO: Test({GUILD}): a(1) issued appcommand: `config` with arguments: {{}}\n",
	]


class TestQuickLeaves(unittest.TestCase) :

	def setUp(self) :
		self.folder = tempfile.TemporaryDirectory()
		self.now = datetime.now()
		self.log = os.path.join(self.folder.name, "log.txt")
		with open(self.log, "w", encoding="utf-8") as file :
			file.writelines(_log_lines(self.now))

	# ============================================================
	def tearDown(self) :
		self.folder.cleanup()

	# ============================================================
	def _records(self, since: datetime) :
		return quickleaves.server_records(GUILD, read_records(since, [self.log]))

	# ============================================================
	def test_records_and_lookups(self) :
		records = self._records(self.now - timedelta(days=1))
		commands = quickleaves.command_counts(records)

		self.assertEqual(len(records), 6)
		self.assertIn("KeyError: 'modchannel'", records[4].text)
		self.assertEqual(commands, {"lookup" : 2, "checkall" : 1, "config" : 1})
		self.assertEqual(quickleaves.lookup_count(commands), 3)

	# ============================================================
	def test_build_file(self) :
		joined = datetime(2026, 9, 27, 10, tzinfo=timezone.utc)
		text = quickleaves.build_file(GUILD, "Test", "owner(5)", 40, joined, joined + timedelta(hours=5),
		                              self._records(self.now - timedelta(days=1)), {"added" : 12, "shared" : 9})

		self.assertIn(f"Server: Test ({GUILD})", text)
		self.assertIn("Time in server: 5h 0m", text)
		self.assertIn("Network lookups: 3", text)
		self.assertIn("Bans added: 12", text)
		self.assertIn("Bans still shared: 9", text)
		self.assertIn("Server Info: Test", text)

	# ============================================================
	def _guild(self, joined_at) :
		return SimpleNamespace(id=GUILD, name="Test", owner="owner", owner_id=5, member_count=40,
		                       me=SimpleNamespace(joined_at=joined_at))

	# ============================================================
	def _capture(self, guild, folder) :
		stats = MagicMock()
		stats.bans_from_server.return_value = {"added" : 4, "shared" : 4}
		records = lambda since : read_records(since, [self.log])
		with patch.object(quickleaves, "QUICK_LEAVE_DIR", folder), \
				patch.object(quickleaves, "read_records", side_effect=records), \
				patch.object(quickleaves, "StatsTransactions", return_value=stats), \
				patch.object(quickleaves.asyncio, "sleep", new=AsyncMock()) :
			return asyncio.run(quickleaves.capture(guild))

	# ============================================================
	def test_capture_saves_a_join_leaver(self) :
		folder = os.path.join(self.folder.name, "quick")
		path = self._capture(self._guild(datetime.now(tz=timezone.utc) - timedelta(hours=4)), folder)

		self.assertIsNotNone(path)
		saved = quickleaves.saved_since(self.now - timedelta(minutes=5), folder)
		self.assertEqual(len(saved), 1)
		self.assertEqual((saved[0].commands, saved[0].lookups, saved[0].bans_added), (4, 3, 4))

	# ============================================================
	def test_capture_skips_a_server_that_stayed(self) :
		folder = os.path.join(self.folder.name, "quick")
		guild = self._guild(datetime.now(tz=timezone.utc) - timedelta(days=quickleaves.QUICK_LEAVE_DAYS + 1))

		self.assertIsNone(self._capture(guild, folder))
		self.assertFalse(os.path.exists(folder))

	# ============================================================
	def test_capture_skips_a_server_without_commands(self) :
		folder = os.path.join(self.folder.name, "quick")

		self.assertIsNone(self._capture(self._guild(datetime.now(tz=timezone.utc) - timedelta(minutes=5)), folder))

	# ============================================================
	def test_prune_removes_only_expired_files(self) :
		folder = os.path.join(self.folder.name, "quick")
		os.makedirs(folder)
		old, new = os.path.join(folder, "old.txt"), os.path.join(folder, "new.txt")
		for path in (old, new) :
			with open(path, "w") as file :
				file.write("Server: x\n")
		expired = (self.now - timedelta(days=quickleaves.QUICK_LEAVE_RETENTION_DAYS + 1)).timestamp()
		os.utime(old, (expired, expired))

		self.assertEqual(quickleaves.prune(self.now, folder), 1)
		self.assertEqual(os.listdir(folder), ["new.txt"])
