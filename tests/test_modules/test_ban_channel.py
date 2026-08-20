"""Unit tests for the ban-channel fallback in classes/ban/ban_channel.py.

When a server has no usable mod channel, the ban flow must not fail silently: it warns the
server in a random channel it CAN post in. These tests pin the two properties that matter:

  1. the warning is delivered (and rate limited per guild + source), and
  2. ban details never leak into the fallback channel - the fallback channel is chosen
     because it is reachable, not because it is private.

No live Discord or DB rows are needed; channels/guilds are synthetic and permissions are
driven through permissions_for().
"""
import logging
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from classes.ban import ban_channel
from classes.ban.BanChecker import BanChecker, BanCheckerStatus


# --------------------------------------------------------------------------------------
# Test doubles
# --------------------------------------------------------------------------------------
def make_channel(name, *, can_view=True, can_send=True, can_embed=True, channel_id=None) :
	"""A discord.TextChannel stand-in whose permissions_for() answers the bot's checks."""
	channel = MagicMock(spec=discord.TextChannel)
	channel.name = name
	channel.id = channel_id if channel_id is not None else abs(hash(name)) % 10 ** 8
	perms = MagicMock()
	perms.view_channel = can_view
	perms.send_messages = can_send
	perms.embed_links = can_embed
	channel.permissions_for.return_value = perms
	channel.send = AsyncMock()
	return channel


# ============================================================
def make_guild(channels, *, name="Test Guild", gid=1) :
	guild = MagicMock(spec=discord.Guild)
	guild.id = gid
	guild.name = name
	guild.icon = None
	guild.text_channels = channels
	guild.me = MagicMock()
	guild.owner = MagicMock()
	guild.owner.send = AsyncMock()
	for channel in channels :
		channel.guild = guild
	return guild


# ============================================================
def sent_text(channel) -> str :
	"""Everything that was actually delivered to `channel`, flattened to one lower-case string."""
	parts = []
	for call in channel.send.await_args_list :
		parts.extend(str(arg) for arg in call.args)
		embed = call.kwargs.get("embed")
		if isinstance(embed, discord.Embed) :
			parts.extend([str(embed.title), str(embed.description), str(embed.footer.text)])
			parts.extend(f"{field.name} {field.value}" for field in embed.fields)
		if call.kwargs.get("content") :
			parts.append(str(call.kwargs["content"]))
	return " ".join(parts).lower()


class BanChannelTestCase(unittest.IsolatedAsyncioTestCase) :
	def setUp(self) :
		# The failure paths log warnings on purpose; keep test output clean.
		logging.disable(logging.CRITICAL)
		self.addCleanup(logging.disable, logging.NOTSET)
		# The cooldown cache is module-level state; a leftover entry would mute another test.
		ban_channel._last_warning.clear()


# --------------------------------------------------------------------------------------
# can_send / pick_fallback_channel
# --------------------------------------------------------------------------------------
class CanSend(BanChannelTestCase) :
	def test_writable_channel(self) :
		self.assertTrue(ban_channel.can_send(make_channel("general")))

	# ============================================================
	def test_missing_permissions(self) :
		self.assertFalse(ban_channel.can_send(make_channel("locked", can_send=False)))
		self.assertFalse(ban_channel.can_send(make_channel("hidden", can_view=False)))

	# ============================================================
	def test_non_channels(self) :
		# None (unset config) and a User (get_channel's owner fallback) are not places we post.
		self.assertFalse(ban_channel.can_send(None))
		self.assertFalse(ban_channel.can_send(MagicMock(spec=discord.User)))


class PickFallbackChannel(BanChannelTestCase) :
	def test_only_writable_channels_are_candidates(self) :
		locked = make_channel("locked", can_send=False)
		unseen = make_channel("unseen", can_view=False)
		guild = make_guild([locked, unseen] + [make_channel(f"open-{i}") for i in range(4)])
		picked = {ban_channel.pick_fallback_channel(guild).name for _ in range(60)}
		self.assertNotIn("locked", picked)
		self.assertNotIn("unseen", picked)

	# ============================================================
	def test_picks_randomly(self) :
		# Not first-match: #rules / #announcements should not absorb every warning.
		guild = make_guild([make_channel(f"open-{i}") for i in range(5)])
		picked = {ban_channel.pick_fallback_channel(guild).name for _ in range(60)}
		self.assertGreater(len(picked), 1)

	# ============================================================
	def test_exclude_is_respected(self) :
		channels = [make_channel(f"open-{i}") for i in range(3)]
		guild = make_guild(channels)
		picked = {ban_channel.pick_fallback_channel(guild, exclude=channels[0]).name for _ in range(60)}
		self.assertNotIn(channels[0].name, picked)

	# ============================================================
	def test_no_writable_channel(self) :
		guild = make_guild([make_channel("locked", can_send=False)])
		self.assertIsNone(ban_channel.pick_fallback_channel(guild))


# --------------------------------------------------------------------------------------
# resolve_ban_channel
# --------------------------------------------------------------------------------------
class ResolveBanChannel(BanChannelTestCase) :
	async def _resolve(self, guild, configured) :
		config = MagicMock()
		config.return_value.get_channel = AsyncMock(return_value=configured)
		with patch("classes.ban.ban_channel.ConfigData", config) :
			return await ban_channel.resolve_ban_channel(guild)

	# ============================================================
	async def test_unset_channel(self) :
		self.assertIsNone(await self._resolve(make_guild([make_channel("open")]), None))

	# ============================================================
	async def test_configured_but_unwritable(self) :
		locked = make_channel("locked", can_send=False)
		self.assertIsNone(await self._resolve(make_guild([locked]), locked))

	# ============================================================
	async def test_configured_and_writable(self) :
		mod = make_channel("mod-log")
		self.assertIs(await self._resolve(make_guild([mod]), mod), mod)


# --------------------------------------------------------------------------------------
# warn_missing_ban_channel
# --------------------------------------------------------------------------------------
class WarnMissingBanChannel(BanChannelTestCase) :
	async def test_warning_is_delivered_to_one_channel(self) :
		guild = make_guild([make_channel(f"open-{i}") for i in range(4)])
		self.assertTrue(await ban_channel.warn_missing_ban_channel(guild, source="ban"))
		posted = [c for c in guild.text_channels if c.send.await_count]
		self.assertEqual(len(posted), 1)

	# ============================================================
	async def test_warning_is_actionable(self) :
		guild = make_guild([make_channel("open")], name="Cool Server")
		await ban_channel.warn_missing_ban_channel(guild, problem=ban_channel.UNSET, source="ban")
		text = sent_text(guild.text_channels[0])
		self.assertIn("cool server", text)         # owners run several servers; name it
		self.assertIn("/config change", text)      # and say how to fix it

	# ============================================================
	async def test_warning_carries_no_ban_details(self) :
		# The fallback channel may be public. Nothing about the ban may appear in it.
		guild = make_guild([make_channel("open")])
		await ban_channel.warn_missing_ban_channel(guild, source="ban")
		text = sent_text(guild.text_channels[0])
		for leak in ("banned user", "ban reason", "reason:", "user id") :
			self.assertNotIn(leak, text)

	# ============================================================
	async def test_repeat_warnings_are_rate_limited_per_source(self) :
		guild = make_guild([make_channel("open")])
		self.assertTrue(await ban_channel.warn_missing_ban_channel(guild, source="ban"))
		# Ten bans in a row must not produce ten warnings...
		self.assertFalse(await ban_channel.warn_missing_ban_channel(guild, source="ban"))
		# ...but a slow background sweep is tracked separately, so it can still speak once.
		self.assertTrue(await ban_channel.warn_missing_ban_channel(guild, source="sweep"))

	# ============================================================
	async def test_first_warning_is_never_suppressed(self) :
		# Regression: keying "never warned" as 0.0 made the FIRST warning collide with
		# time.monotonic()'s arbitrary epoch, silently swallowing it on a freshly booted host.
		guild = make_guild([make_channel("open")], gid=4242)
		with patch("classes.ban.ban_channel.time.monotonic", return_value=5.0) :
			self.assertTrue(
				await ban_channel.warn_missing_ban_channel(guild, source="ban", cooldown=3600))

	# ============================================================
	async def test_plain_text_when_embeds_are_not_allowed(self) :
		guild = make_guild([make_channel("open", can_embed=False)])
		await ban_channel.warn_missing_ban_channel(guild, source="ban")
		call = guild.text_channels[0].send.await_args
		self.assertIsNone(call.kwargs.get("embed"))
		self.assertIsInstance(call.args[0], str)

	# ============================================================
	async def test_owner_dm_is_the_last_resort(self) :
		guild = make_guild([make_channel("locked", can_send=False)])
		self.assertTrue(await ban_channel.warn_missing_ban_channel(guild, source="ban"))
		guild.owner.send.assert_awaited_once()

	# ============================================================
	async def test_never_raises(self) :
		# Called from the ban path: a failure here must never take the ban flow down.
		self.assertFalse(await ban_channel.warn_missing_ban_channel(None))
		guild = make_guild([make_channel("boom")])
		guild.text_channels[0].send.side_effect = discord.Forbidden(MagicMock(status=403), "nope")
		self.assertFalse(await ban_channel.warn_missing_ban_channel(guild, source="ban"))


# --------------------------------------------------------------------------------------
# BanChecker.send_review_prompt - the ban flow's use of the fallback
# --------------------------------------------------------------------------------------
class SendReviewPrompt(BanChannelTestCase) :
	def _checker(self, reason="raiding the server repeatedly") :
		ban = MagicMock()
		ban.reason = reason
		ban.user = MagicMock()
		ban.user.id = 1111
		ban.user.name = "tester"
		ban.user.__str__ = lambda self : "tester"
		checker = BanChecker(bot=MagicMock(), ban=ban)
		checker.status = BanCheckerStatus.PROMPT
		return checker

	# ============================================================
	async def test_prompt_goes_to_the_mod_channel(self) :
		mod = make_channel("mod-log")
		guild = make_guild([mod, make_channel("general")])
		checker = self._checker()
		queued = []
		with patch("classes.ban.BanChecker.resolve_ban_channel", AsyncMock(return_value=mod)), \
			patch("classes.ban.BanChecker.ConfigData"), \
			patch("classes.ban.BanChecker.warn_missing_ban_channel", AsyncMock()) as warn, \
			patch("classes.ban.BanChecker.queue") as queue_cls :
			queue_cls.return_value.add = lambda task, priority=1 : queued.append(task)
			await checker.send_review_prompt(guild)
			for task in queued :
				await task
		warn.assert_not_awaited()
		mod.send.assert_awaited_once()

	# ============================================================
	async def test_no_mod_channel_warns_instead_of_leaking_the_prompt(self) :
		# The prompt embed names the banned user and quotes the reason, so it must NOT be
		# redirected to the fallback channel - only the detail-free warning goes there.
		general = make_channel("general")
		guild = make_guild([general])
		checker = self._checker()
		with patch("classes.ban.BanChecker.resolve_ban_channel", AsyncMock(return_value=None)), \
			patch("classes.ban.BanChecker.ConfigData"), \
			patch("classes.ban.BanChecker.warn_missing_ban_channel", AsyncMock()) as warn, \
			patch("classes.ban.BanChecker.queue") as queue_cls :
			await checker.send_review_prompt(guild)
		warn.assert_awaited_once()
		general.send.assert_not_awaited()
		queue_cls.return_value.add.assert_not_called()

	# ============================================================
	async def test_failed_delivery_falls_back_to_a_warning(self) :
		# Permissions can change between the check and the send; the queue would otherwise
		# swallow the error and leave the server thinking the ban was handled.
		mod = make_channel("mod-log")
		mod.send.side_effect = discord.Forbidden(MagicMock(status=403), "nope")
		guild = make_guild([mod, make_channel("general")])
		checker = self._checker()
		with patch("classes.ban.BanChecker.warn_missing_ban_channel", AsyncMock()) as warn :
			await checker._deliver_review_prompt(guild, mod, discord.Embed(title="x"), None)
		warn.assert_awaited_once()
		self.assertEqual(warn.await_args.kwargs.get("problem"), ban_channel.UNREACHABLE)
		# and never back into the channel we just failed on
		self.assertIs(warn.await_args.kwargs.get("exclude"), mod)


if __name__ == "__main__" :
	unittest.main()
