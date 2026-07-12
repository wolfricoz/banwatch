"""Unit tests for the ban DECISION logic in classes/ban/BanChecker.py.

These tests exercise the vetting rules (cross-ban, low-value, migrated, short-reason,
flagged-terms, PII) and the run()/short_run()/evaluate_ban orchestration WITHOUT a live
Discord connection - they feed synthetic BanEntry objects and mock the two DB/service
dependencies (AccessControl, TermsChecker). This is the layer where the cross-ban and
low-value bugs previously shipped undetected; see tests/run_tests.py for the history.
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from classes.ban.BanChecker import BanChecker, BanCheckerStatus
from resources.bans.BanCheckVariables import BAN_STARTS_WITH, IGNORED_REASONS

PROMPT = BanCheckerStatus.PROMPT
HIDE = BanCheckerStatus.HIDE
REVIEW = BanCheckerStatus.REVIEW
SHORT = BanCheckerStatus.SHORT


# --------------------------------------------------------------------------------------
# Test doubles (no live Discord / DB rows needed for the decision logic)
# --------------------------------------------------------------------------------------
class FakeUser :
	def __init__(self, uid=1111, is_bot=False, name="tester") :
		self.id = uid
		self.bot = is_bot
		self.name = name

	def __str__(self) :
		return self.name


class FakeBan :
	"""Stands in for discord.BanEntry - only .reason and .user are read by BanChecker."""
	def __init__(self, reason, user=None) :
		self.reason = reason
		self.user = user if user is not None else FakeUser()


class FakeTerms :
	"""Stands in for classes.TermsChecker.TermsChecker."""
	def __init__(self, review_status="", result="", found=None) :
		self._review_status = review_status
		self._result = result
		self._found = found if found is not None else []

	def getReviewStatus(self) :
		return self._review_status

	def getResults(self) :
		return self._result, self._found


def make_checker(reason, *, is_bot=False, uid=1111) :
	ban = FakeBan(reason, FakeUser(uid=uid, is_bot=is_bot))
	return BanChecker(bot=MagicMock(), ban=ban)


def terms_factory(mapping) :
	"""Return a TermsChecker replacement. `mapping` maps action name ->
	(review_status, result, found). Unlisted actions return an empty (no-hit) checker."""
	def factory(action, target) :
		review_status, result, found = mapping.get(action, ("", "", []))
		return FakeTerms(review_status, result, found)
	return factory


# --------------------------------------------------------------------------------------
# check_cross_ban
# --------------------------------------------------------------------------------------
class CrossBanCheck(unittest.IsolatedAsyncioTestCase) :
	async def test_cross_ban_formats_are_hidden(self) :
		reasons = [
			"Cross-ban from CoolServer with ban id: 12345",
			"Cross-ban from CoolServer with ban id: 12345 with reason: raiding",
			"Cross-ban from CoolServer: they were raiding",     # manual format (lookup.py:58)
			"Cross-ban from (CoolServer): spamming",
			"cross-ban from coolserver: lowercase",             # case-insensitive
			"Cross ban from CoolServer",                        # space variant
			"crossban from CoolServer",                         # no separator
			"crossban",
			"cross-ban",
			"cross ban",
			"  Cross-ban from X  ",                             # surrounding whitespace
		]
		for reason in reasons :
			with self.subTest(reason=reason) :
				checker = make_checker(reason)
				await checker.check_cross_ban()
				self.assertEqual(checker.status, HIDE)
				self.assertEqual(checker.reason, "Cross ban")

	async def test_non_cross_bans_are_not_hidden(self) :
		reasons = [
			"Spamming and raiding",
			"Banned for posting a cross-ban notice in chat",   # merely mentions it
			"No reason provided",
			"crossbanana",
			"",
			"None",
		]
		for reason in reasons :
			with self.subTest(reason=reason) :
				checker = make_checker(reason)
				await checker.check_cross_ban()
				self.assertEqual(checker.status, PROMPT)


# --------------------------------------------------------------------------------------
# assess_value (low-value / hidden-tag reasons)
# --------------------------------------------------------------------------------------
class AssessValueCheck(unittest.IsolatedAsyncioTestCase) :
	async def test_low_value_reasons_are_hidden(self) :
		reasons = [
			None,
			"",
			"none",
			"None",                        # case-insensitive
			"account has no avatar",
			"no reason given",
			"breaking server rules",
			"n/a",
			"test",
			"  BREAKING SERVER RULES  ",   # strip + lowercase
			"[hidden] internal note",      # BAN_STARTS_WITH prefix
			"no pfp lol",                  # BAN_STARTS_WITH prefix
			"no reason specified by the moderator",  # substring match
		]
		for reason in reasons :
			with self.subTest(reason=reason) :
				checker = make_checker(reason)
				await checker.assess_value()
				self.assertEqual(checker.status, HIDE)
				self.assertEqual(checker.reason, "Low Value Ban")

	async def test_valuable_reasons_are_not_hidden(self) :
		reasons = [
			"Raiding the server repeatedly",
			"Posting NSFW content in general chat",
			# Documents current behaviour: assess_value does NOT catch Discord's
			# "No reason provided" default - it is later caught by check_word_count as SHORT.
			"No reason provided",
		]
		for reason in reasons :
			with self.subTest(reason=reason) :
				checker = make_checker(reason)
				await checker.assess_value()
				self.assertEqual(checker.status, PROMPT)

	async def test_variables_stay_normalised(self) :
		# Guard against someone adding an upper-case / padded entry that would silently never match.
		for entry in IGNORED_REASONS :
			self.assertEqual(entry, entry.lower().strip(), f"IGNORED_REASONS entry not normalised: {entry!r}")
		for entry in BAN_STARTS_WITH :
			self.assertEqual(entry, entry.lower(), f"BAN_STARTS_WITH entry not lowercase: {entry!r}")


# --------------------------------------------------------------------------------------
# migrated_ban
# --------------------------------------------------------------------------------------
class MigratedBanCheck(unittest.IsolatedAsyncioTestCase) :
	async def test_migrated_tag_is_hidden(self) :
		for reason in ("[migrated] old ban", "[Migrated] Old Ban", "[MIGRATED]") :
			with self.subTest(reason=reason) :
				checker = make_checker(reason)
				await checker.migrated_ban()
				self.assertEqual(checker.status, HIDE)
				self.assertEqual(checker.reason, "Migrated ban")

	async def test_non_migrated_is_untouched(self) :
		for reason in ("migrated from old system", "raiding", "") :
			with self.subTest(reason=reason) :
				checker = make_checker(reason)
				await checker.migrated_ban()
				self.assertEqual(checker.status, PROMPT)


# --------------------------------------------------------------------------------------
# check_bot
# --------------------------------------------------------------------------------------
class BotCheck(unittest.IsolatedAsyncioTestCase) :
	async def test_bot_user_is_flagged_for_review(self) :
		checker = make_checker("some reason", is_bot=True)
		await checker.check_bot()
		self.assertEqual(checker.status, REVIEW)
		self.assertEqual(checker.reason, "Member is a bot")

	async def test_human_user_is_untouched(self) :
		checker = make_checker("some reason", is_bot=False)
		await checker.check_bot()
		self.assertEqual(checker.status, PROMPT)


# --------------------------------------------------------------------------------------
# check_word_count (short-reason rule + spam/bot word-boundary allow-through)
# --------------------------------------------------------------------------------------
class WordCountCheck(unittest.IsolatedAsyncioTestCase) :
	async def test_short_reasons_become_short(self) :
		# < 4 words and not a genuine "spam"/"bot" mention
		for reason in ("raiding", "ban evasion alt", "alt account", "a  b  c") :
			with self.subTest(reason=reason) :
				checker = make_checker(reason)
				await checker.check_word_count()
				self.assertEqual(checker.status, SHORT)

	async def test_none_reason_is_short(self) :
		checker = make_checker(None)
		await checker.check_word_count()
		self.assertEqual(checker.status, SHORT)

	async def test_spam_or_bot_wholewords_are_kept(self) :
		# Genuine keyword reasons are NOT marked short even though they are < 4 words.
		for reason in ("spam", "bot", "spam bot", "Spam account", "raid bot") :
			with self.subTest(reason=reason) :
				checker = make_checker(reason)
				await checker.check_word_count()
				self.assertEqual(checker.status, PROMPT)

	async def test_substring_lookalikes_are_still_short(self) :
		# The old substring bug: these contain "spam"/"bot" as substrings but are not the word.
		for reason in ("robot", "sabotage", "bots", "xXspammerXx") :
			with self.subTest(reason=reason) :
				checker = make_checker(reason)
				await checker.check_word_count()
				self.assertEqual(checker.status, SHORT)

	async def test_long_reasons_are_untouched(self) :
		for reason in ("posted spam links repeatedly in general", "this is a sufficiently detailed reason") :
			with self.subTest(reason=reason) :
				checker = make_checker(reason)
				await checker.check_word_count()
				self.assertEqual(checker.status, PROMPT)


# --------------------------------------------------------------------------------------
# check_pii
# --------------------------------------------------------------------------------------
class PiiCheck(unittest.IsolatedAsyncioTestCase) :
	async def test_pii_is_flagged_for_review(self) :
		for reason in (
			"contact me at foo.bar@example.com please",
			"his number is 555-123-4567",
			"born 12/31/1990 for reference",
		) :
			with self.subTest(reason=reason) :
				checker = make_checker(reason)
				await checker.check_pii()
				self.assertEqual(checker.status, REVIEW)

	async def test_clean_reasons_are_untouched(self) :
		for reason in ("just a normal ban reason", "") :
			with self.subTest(reason=reason) :
				checker = make_checker(reason)
				await checker.check_pii()
				self.assertEqual(checker.status, PROMPT)

	async def test_none_reason_does_not_crash(self) :
		checker = make_checker(None)
		await checker.check_pii()  # must not raise TypeError
		self.assertEqual(checker.status, PROMPT)


# --------------------------------------------------------------------------------------
# _normalise_found (list/tuple -> str; underpins the flagged-term crash fix)
# --------------------------------------------------------------------------------------
class NormaliseFound(unittest.TestCase) :
	def test_normalisation(self) :
		cases = [
			(["slur1", "slur2"], "slur1, slur2"),
			([("a", "b"), ("c", "")], "a, b, c"),   # regex-group tuples flattened, empties dropped
			("already a string", "already a string"),
			([], ""),
			(None, ""),
			(["dup", "dup"], "dup"),                # de-duplicated
		]
		for found, expected in cases :
			with self.subTest(found=found) :
				self.assertEqual(BanChecker._normalise_found(found), expected)


# --------------------------------------------------------------------------------------
# check_flagged_terms (block outranks review; reason always a str)
# --------------------------------------------------------------------------------------
class FlaggedTermsCheck(unittest.IsolatedAsyncioTestCase) :
	async def _run(self, mapping, reason="a flagged reason here") :
		checker = make_checker(reason)
		with patch("classes.ban.BanChecker.TermsChecker", side_effect=terms_factory(mapping)) :
			await checker.check_flagged_terms(checker.ban.reason)
		return checker

	async def test_no_hits_stays_prompt(self) :
		checker = await self._run({})
		self.assertEqual(checker.status, PROMPT)

	async def test_review_hit(self) :
		checker = await self._run({"review": ("review", "review", ["badword"])})
		self.assertEqual(checker.status, REVIEW)
		self.assertEqual(checker.reason, "badword")

	async def test_block_hit(self) :
		checker = await self._run({"block": ("block", "block", ["slur"])})
		self.assertEqual(checker.status, HIDE)
		self.assertEqual(checker.reason, "slur")

	async def test_block_outranks_review(self) :
		# Both fire; block must win and must not be downgraded by a later review.
		checker = await self._run({
			"review": ("review", "review", ["reviewword"]),
			"block": ("block", "block", ["slur"]),
			"countblock": ("review", "review", ["laterreview"]),
		})
		self.assertEqual(checker.status, HIDE)
		self.assertEqual(checker.reason, "slur")

	async def test_first_review_reason_is_kept(self) :
		checker = await self._run({
			"review": ("review", "review", ["first"]),
			"countreview": ("review", "review", ["second"]),
		})
		self.assertEqual(checker.status, REVIEW)
		self.assertEqual(checker.reason, "first")

	async def test_found_list_is_normalised_to_string(self) :
		checker = await self._run({"block": ("block", "block", ["s1", "s2"])})
		self.assertEqual(checker.status, HIDE)
		self.assertIsInstance(checker.reason, str)
		self.assertEqual(checker.reason, "s1, s2")

	async def test_empty_review_status_is_skipped(self) :
		# A checker whose getReviewStatus() is "" is ignored even if getResults() has a verdict.
		checker = await self._run({"block": ("", "block", ["ignored"])})
		self.assertEqual(checker.status, PROMPT)


# --------------------------------------------------------------------------------------
# perform_action (the first-check-wins gate)
# --------------------------------------------------------------------------------------
class PerformAction(unittest.IsolatedAsyncioTestCase) :
	async def test_runs_when_prompt(self) :
		checker = make_checker("x")
		ran = []

		async def action() :
			ran.append(True)

		await checker.perform_action(action())
		self.assertEqual(ran, [True])

	async def test_skips_and_closes_when_not_prompt(self) :
		checker = make_checker("x")
		checker.status = HIDE
		ran = []

		async def action() :
			ran.append(True)

		await checker.perform_action(action())   # coroutine is closed, not awaited
		self.assertEqual(ran, [])
		self.assertEqual(checker.status, HIDE)


# --------------------------------------------------------------------------------------
# run() - full orchestration and first-check-wins priority
# --------------------------------------------------------------------------------------
class RunIntegration(unittest.IsolatedAsyncioTestCase) :
	async def _run(self, reason, *, is_bot=False, staff=False, terms=None) :
		checker = make_checker(reason, is_bot=is_bot)
		with patch("classes.ban.BanChecker.TermsChecker", side_effect=terms_factory(terms or {})), \
			patch("classes.ban.BanChecker.AccessControl") as access :
			access.return_value.access_all.return_value = staff
			await checker.run()
		return checker

	async def test_cross_ban_is_hidden(self) :
		checker = await self._run("Cross-ban from X: raiding")
		self.assertEqual(checker.status, HIDE)

	async def test_low_value_is_hidden(self) :
		checker = await self._run("")
		self.assertEqual(checker.status, HIDE)

	async def test_migrated_is_hidden(self) :
		checker = await self._run("[migrated] legacy ban")
		self.assertEqual(checker.status, HIDE)

	async def test_bot_is_review(self) :
		checker = await self._run("raiding the server today please", is_bot=True)
		self.assertEqual(checker.status, REVIEW)
		self.assertEqual(checker.reason, "Member is a bot")

	async def test_staff_is_review(self) :
		checker = await self._run("raiding the server today please", staff=True)
		self.assertEqual(checker.status, REVIEW)
		self.assertEqual(checker.reason, "Banwatch Staff Member")

	async def test_short_reason_is_short(self) :
		checker = await self._run("raiding")
		self.assertEqual(checker.status, SHORT)

	async def test_pii_is_review(self) :
		checker = await self._run("please contact me foo@bar.com now")
		self.assertEqual(checker.status, REVIEW)

	async def test_normal_reason_prompts(self) :
		checker = await self._run("raiding the whole server repeatedly")
		self.assertEqual(checker.status, PROMPT)

	async def test_cross_ban_beats_short(self) :
		# "cross-ban from X" is < 4 words but cross-ban runs first and wins.
		checker = await self._run("cross-ban from X")
		self.assertEqual(checker.status, HIDE)
		self.assertEqual(checker.reason, "Cross ban")

	async def test_block_term_beats_short(self) :
		# A one-word blocked slur must be HIDE (flagged terms run before the short-reason check).
		checker = await self._run("slur", terms={"block": ("block", "block", ["slur"])})
		self.assertEqual(checker.status, HIDE)


# --------------------------------------------------------------------------------------
# short_run() - lightweight pre-check for the live path
# --------------------------------------------------------------------------------------
class ShortRunIntegration(unittest.IsolatedAsyncioTestCase) :
	async def test_cross_ban_is_hidden(self) :
		checker = make_checker("Cross-ban from X: raiding")
		await checker.short_run()
		self.assertEqual(checker.status, HIDE)

	async def test_low_value_is_hidden(self) :
		checker = make_checker("")
		await checker.short_run()
		self.assertEqual(checker.status, HIDE)

	async def test_migrated_is_hidden(self) :
		checker = make_checker("[migrated] legacy")
		await checker.short_run()
		self.assertEqual(checker.status, HIDE)

	async def test_short_reason_is_not_evaluated(self) :
		# short_run must NOT run the word-count check - a short reason stays PROMPT so the
		# buttons can do the real check.
		checker = make_checker("raiding")
		await checker.short_run()
		self.assertEqual(checker.status, PROMPT)

	async def test_normal_reason_prompts(self) :
		checker = make_checker("raiding the whole server repeatedly")
		await checker.short_run()
		self.assertEqual(checker.status, PROMPT)

	async def test_bot_user_is_not_evaluated(self) :
		# short_run does not run the bot check either.
		checker = make_checker("raiding the whole server repeatedly", is_bot=True)
		await checker.short_run()
		self.assertEqual(checker.status, PROMPT)


# --------------------------------------------------------------------------------------
# evaluate_ban - verdict routing (Bans/queue/config mocked)
# --------------------------------------------------------------------------------------
class EvaluateBanRouting(unittest.IsolatedAsyncioTestCase) :
	def _guild(self) :
		guild = MagicMock()
		guild.id = 999
		guild.name = "Guild"
		guild.owner = MagicMock()
		guild.owner.name = "Owner"
		return guild

	def _bans(self, add_ban_return=None) :
		bans = MagicMock()
		bans.add_ban = AsyncMock(return_value=add_ban_return if add_ban_return is not None else MagicMock())
		bans.check_guilds = AsyncMock()
		return bans

	async def test_hide_records_hidden_with_string_reason(self) :
		checker = make_checker("whatever")
		checker.status = HIDE
		checker.reason = "Cross ban"
		bans = self._bans()
		with patch("classes.bans.Bans", return_value=bans) :
			await checker.evaluate_ban(self._guild(), server_only=False)
		bans.add_ban.assert_awaited_once()
		args, kwargs = bans.add_ban.await_args
		self.assertTrue(kwargs.get("hidden"))
		self.assertTrue(str(args[2]).startswith("Ban hidden:"))  # reason is a str, never a list

	async def test_short_records_unapproved(self) :
		checker = make_checker("raiding")
		checker.status = SHORT
		bans = self._bans()
		with patch("classes.bans.Bans", return_value=bans) :
			await checker.evaluate_ban(self._guild(), server_only=False)
		bans.add_ban.assert_awaited_once()
		_, kwargs = bans.add_ban.await_args
		self.assertFalse(kwargs.get("approved"))

	async def test_review_records_original_reason_unapproved(self) :
		checker = make_checker("some detailed ban reason here")
		checker.status = REVIEW
		checker.reason = "badword"
		bans = self._bans()
		with patch("classes.bans.Bans", return_value=bans) :
			await checker.evaluate_ban(self._guild(), server_only=False)
		args, kwargs = bans.add_ban.await_args
		# NOTE: the REVIEW branch stores the ORIGINAL ban.reason (approved=False). The prefixed
		# "Ban marked for review: ..." (self.reason) is only used for the EvidenceUI in the
		# server_only path, not for the stored ban row.
		self.assertEqual(args[2], "some detailed ban reason here")
		self.assertFalse(kwargs.get("approved"))

	async def test_prompt_shows_review_buttons(self) :
		checker = make_checker("a shareable ban reason")
		checker.status = PROMPT
		with patch.object(checker, "send_review_prompt", AsyncMock()) as prompt :
			await checker.evaluate_ban(self._guild(), server_only=False)
		prompt.assert_awaited_once()

	async def test_prompt_server_only_survives_failed_add(self) :
		# add_ban returns False (e.g. server not registered). The PROMPT server_only branch
		# must guard against that and not crash trying to read ban.reason.
		checker = make_checker("a shareable ban reason")
		checker.status = PROMPT
		bans = self._bans(add_ban_return=False)
		with patch("classes.bans.Bans", return_value=bans) :
			await checker.evaluate_ban(self._guild(), server_only=True)  # must not raise
		bans.check_guilds.assert_not_called()


if __name__ == "__main__" :
	unittest.main()
