import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from classes.support.quickleaves import SavedQuickLeave
from classes.support.weeklyreport import FIELD_LIMIT, LogSummary, WeeklyReport, build_embeds, delta, duration, \
	summarise_logs


def _report(**overrides) -> WeeklyReport :
	end = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)
	bans = {"new" : 20, "hidden" : 3, "verified" : 5, "with_proof" : 15, "removed" : 2}
	appeals = {"new" : 4, "approved" : 1, "denied" : 3, "messages" : 10, "pending" : 2,
	           "oldest_age" : timedelta(days=2, hours=1)}
	values = dict(
		start=end - timedelta(days=7), end=end,
		bans=bans, previous_bans=dict(bans, new=10),
		review={"waiting" : 7, "oldest_age" : timedelta(hours=5)},
		top_servers=[("A server", 8), ("B*server", 2)],
		appeals=appeals, previous_appeals=dict(appeals, new=0),
		warnings={"new" : 6, "evidence" : 9},
		servers={"new" : 2, "active" : 300, "members" : 90000, "hidden" : 4, "premium_expiring" : 1},
		guilds_connected=301, latency_ms=55, queue_status="Remaining queue: High: 0",
		online_since=datetime(2026, 9, 20, tzinfo=timezone.utc),
		logs=LogSummary(errors=4, warnings=9, joins=5, leaves=3, top_errors=[("Something broke #", 3)]),
	)
	values.update(overrides)
	return WeeklyReport(**values)


def _text(report: WeeklyReport) -> str :
	return "\n".join(f.value for embed in build_embeds(report) for f in embed.fields)


class TestWeeklyReport(unittest.TestCase) :

	def test_helpers(self) :
		self.assertEqual(delta(20, 10), "▲ 100%")
		self.assertEqual(delta(0, 0), "—")
		self.assertEqual(delta(3, 0), "new")
		self.assertEqual(duration(None), "—")
		self.assertEqual(duration(timedelta(days=2, hours=1)), "2d 1h")

	# ============================================================
	def test_build_embeds(self) :
		embeds = build_embeds(_report())
		text = _text(_report())

		self.assertEqual(len(embeds), 3)
		self.assertLess(sum(len(embed) for embed in embeds), 6000)
		self.assertIn("Bans recorded: **20** (▲ 100%)", text)
		self.assertIn("With evidence: **15** (75%", text)
		self.assertIn("Oldest waiting: **5h 0m**", text)
		self.assertIn("approval rate 25%", text)
		self.assertIn("Joined: **5** · Left: **3**", text)
		self.assertIn("-1 vs the database", text)
		self.assertIn("B\\*server", text)

	# ============================================================
	def test_join_leavers_are_flagged(self) :
		saved = [SavedQuickLeave("Harvester (1)", "2h 5m", 9, 8, 0, "a.txt"),
		         SavedQuickLeave("Dumper (2)", "1h 0m", 2, 0, 40, "b.txt")]
		saved += [SavedQuickLeave(f"Other ({i})", "3h 0m", 1, 0, 0, "c.txt") for i in range(5)]
		text = _text(_report(quick_leaves=saved))

		self.assertIn("**7** server(s) removed Banwatch", text)
		self.assertIn("Harvester (1): 2h 5m, 9 command(s) · 🔍 8 lookup(s)", text)
		self.assertIn("Dumper (2): 1h 0m, 2 command(s) · 🔨 40 ban(s) added", text)
		self.assertIn("…and 2 more", text)

	# ============================================================
	def test_empty_week_and_field_limits(self) :
		empty = dict.fromkeys(("new", "hidden", "verified", "with_proof", "removed"), 0)
		report = _report(bans=empty, previous_bans=empty, review={"waiting" : 0, "oldest_age" : None},
		                 top_servers=[("x" * 200, i) for i in range(40)], latency_ms=None, logs=LogSummary())

		for embed in build_embeds(report) :
			for f in embed.fields :
				self.assertTrue(f.value)
				self.assertLessEqual(len(f.value), FIELD_LIMIT)

	# ============================================================
	def test_summarise_logs(self) :
		now = datetime.now()
		new = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
		old = (now - timedelta(days=9)).strftime("%Y-%m-%d %H:%M:%S")
		lines = [
			f"{old},001:root:INFO: Old joined, refreshing ban list\n",
			f"{new},001:root:INFO: A server joined, refreshing ban list\n",
			f"{new},002:root:INFO: B server left, refreshing ban list\n",
			f"{new},003:root:ERROR: Failed for ban 123\n",
			f"{new},004:root:ERROR: Failed for ban 456\n",
			f"{new},005:root:WARNING: slow\n",
		]
		with tempfile.TemporaryDirectory() as folder :
			path = os.path.join(folder, "log.txt")
			with open(path, "w", encoding="utf-8") as file :
				file.writelines(lines)
			summary = summarise_logs(now - timedelta(days=7), [path])

		self.assertEqual((summary.joins, summary.leaves, summary.errors, summary.warnings), (1, 1, 2, 1))
		self.assertEqual(summary.top_errors, [("Failed for ban #", 2)])
