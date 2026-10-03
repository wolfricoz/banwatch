import asyncio
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from classes.support import leavereport
from classes.support.leavereport import LeaveInfo

GUILD = 612345678901234567
CHANNEL = 123


def _guild(joined_at) :
	return SimpleNamespace(id=GUILD, name="Test", owner="owner", owner_id=5, member_count=40,
	                       created_at=datetime(2020, 1, 1, tzinfo=timezone.utc), me=SimpleNamespace(joined_at=joined_at))


def _fields(embed) -> dict :
	return {field.name : str(field.value) for field in embed.fields}


class TestLeaveReport(unittest.TestCase) :

	def setUp(self) :
		self.now = datetime.now(tz=timezone.utc)

	# ============================================================
	def _info(self, **overrides) :
		values = dict(joined_at=self.now - timedelta(hours=5), left_at=self.now, first_added=self.now - timedelta(days=60),
		              bans={"added" : 12, "shared" : 9}, shared_total=30, premium=None, hidden=False,
		              blacklisted=False)
		values.update(overrides)
		return LeaveInfo(**values)

	# ============================================================
	def test_embed_summarises_the_stay(self) :
		embed = leavereport.build_embed(_guild(None), self._info(), 100)
		fields = _fields(embed)

		self.assertEqual(fields["Owner"], "`owner(5)`")
		self.assertEqual(fields["Time in server"], "5h 0m")
		self.assertIn("this was a rejoin", fields["First added"])
		self.assertEqual(fields["Bans added this stay"], "12 (9 still shared)")
		self.assertEqual(fields["Shared bans (all time)"], "30")
		self.assertNotIn("Flags", fields)
		self.assertNotIn("⚠️ Join-leaver", fields)
		self.assertEqual(embed.footer.text, str(GUILD))

	# ============================================================
	def test_embed_flags_and_join_leaver(self) :
		info = self._info(first_added=self.now - timedelta(hours=5), premium=self.now + timedelta(days=3),
		                  blacklisted=True, quick_leave={"Commands" : "4", "Network lookups" : "3"})
		fields = _fields(leavereport.build_embed(_guild(None), info, 100))

		self.assertNotIn("First added", fields)
		self.assertIn("Premium until", fields["Flags"])
		self.assertIn("Blacklisted", fields["Flags"])
		self.assertIn("Network lookups: 3", fields["⚠️ Join-leaver"])

	# ============================================================
	def test_embed_without_join_date(self) :
		fields = _fields(leavereport.build_embed(_guild(None), self._info(joined_at=None, bans=None), 100))

		self.assertEqual(fields["Joined"], "unknown")
		self.assertNotIn("Time in server", fields)
		self.assertNotIn("Bans added this stay", fields)

	# ============================================================
	def _send(self, path) :
		channel = MagicMock()
		bot = SimpleNamespace(guilds=[1, 2], get_channel=MagicMock(return_value=channel))
		sent = AsyncMock()
		with patch.dict(os.environ, {"BANS" : str(CHANNEL)}), \
				patch.object(leavereport.quickleaves, "capture", new=AsyncMock(return_value=path)), \
				patch.object(leavereport, "_gather", return_value=self._info()), \
				patch.object(leavereport.Configer, "is_blacklisted", new=AsyncMock(return_value=None)), \
				patch.object(leavereport, "send_message", new=sent) :
			asyncio.run(leavereport.send(bot, _guild(self.now - timedelta(hours=5))))
		bot.get_channel.assert_called_once_with(CHANNEL)
		return sent

	# ============================================================
	def test_send_posts_to_the_approval_channel(self) :
		sent = self._send(None)

		sent.assert_awaited_once()
		self.assertIsNone(sent.await_args.kwargs["files"])
		self.assertNotIn("⚠️ Join-leaver", _fields(sent.await_args.kwargs["embed"]))

	# ============================================================
	def test_send_attaches_the_join_leaver_file(self) :
		with tempfile.TemporaryDirectory() as folder :
			path = os.path.join(folder, "2026-09-29_1.txt")
			with open(path, "w", encoding="utf-8") as file :
				file.write("Server: Test\nCommands: 4\nNetwork lookups: 3\n\nlog lines\n")
			sent = self._send(path)
			files = sent.await_args.kwargs["files"]
			for f in files :
				f.close()

		self.assertEqual(files[0].filename, "2026-09-29_1.txt")
		self.assertIn("Commands: 4", _fields(sent.await_args.kwargs["embed"])["⚠️ Join-leaver"])
