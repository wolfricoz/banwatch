"""Unit tests for Bans.approve_ban, classes/bans.py.

approve_ban is the headless twin of the "Approve without Proof" button: /staff approve_pending has
no review message to read an embed off, so this rebuilds it from the ban row. Two things matter.
It must hand check_guilds - which is what actually flips approved and broadcasts - the same shape
of arguments the button does, footer format included, because get_ban_id() parses the ban id back
out of that footer. And it must refuse, rather than half-approve, when the guild or user cannot be
resolved: a ban it skips stays pending and comes back on the next sweep.
"""
import logging
import unittest
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from classes.bans import Bans


class ApproveBan(unittest.IsolatedAsyncioTestCase) :
	BAN_ID = 4321
	GUILD_ID = 4000
	USER_ID = 321

	def setUp(self) :
		logging.disable(logging.CRITICAL)
		self.addCleanup(logging.disable, logging.NOTSET)

		self.stack = ExitStack()
		self.addCleanup(self.stack.close)
		self.queue = self.stack.enter_context(patch("classes.bans.queue"))
		self.check_guilds = self.stack.enter_context(
			patch.object(Bans, "check_guilds", new=AsyncMock()))
		# notify_origin_server is a coroutine function handed to queue().add(); with the queue
		# mocked it would never be awaited, so swap it for a plain mock.
		self.stack.enter_context(patch.object(Bans, "notify_origin_server", new=MagicMock()))

		self.ban = MagicMock(ban_id=self.BAN_ID, gid=self.GUILD_ID, uid=self.USER_ID, reason="scammer")
		self.ban.guild.invite = "discord.gg/test"

		self.guild = MagicMock(spec=discord.Guild)
		self.guild.id = self.GUILD_ID
		self.guild.__str__ = lambda _ : "Test Guild"
		self.guild.owner = "owner#0001"

		self.user = MagicMock(spec=discord.User)
		self.user.id = self.USER_ID
		self.user.__str__ = lambda _ : "banned_user"

		self.bot = MagicMock()
		self.bot.get_guild.return_value = self.guild
		self.bot.get_user.return_value = self.user
		self.bot.fetch_user = AsyncMock(return_value=self.user)

	# ============================================================
	async def test_cached_guild_and_user_are_broadcast(self) :
		self.assertTrue(await Bans().approve_ban(self.bot, self.ban))

		self.check_guilds.assert_awaited_once()
		interaction, bot, guild, user, embed, wait_id, open_thread = self.check_guilds.await_args.args
		# interaction is None: there is no review message for a bulk approval to delete.
		self.assertIsNone(interaction)
		self.assertIs(bot, self.bot)
		self.assertIs(guild, self.guild)
		self.assertIs(user, self.user)
		self.assertEqual(wait_id, self.BAN_ID)
		self.assertFalse(open_thread)
		self.assertEqual(embed.description, "scammer")
		# get_ban_id() regexes the id back out of this footer, so the format is load bearing.
		self.assertIn(f"ban ID: {self.BAN_ID}", embed.footer.text)
		self.assertIn("discord.gg/test", embed.footer.text)

	# ============================================================
	async def test_origin_server_is_notified(self) :
		await Bans().approve_ban(self.bot, self.ban)
		Bans().notify_origin_server.assert_called_once_with(self.bot, self.BAN_ID)
		self.queue.return_value.add.assert_called_once()

	# ============================================================
	async def test_uncached_user_is_fetched(self) :
		self.bot.get_user.return_value = None
		self.assertTrue(await Bans().approve_ban(self.bot, self.ban))
		self.bot.fetch_user.assert_awaited_once_with(self.USER_ID)
		self.check_guilds.assert_awaited_once()

	# ============================================================
	async def test_uncached_guild_is_skipped(self) :
		# No fetch_guild fallback: the broadcast path needs a cached guild for get_channel/owner.
		self.bot.get_guild.return_value = None
		self.assertFalse(await Bans().approve_ban(self.bot, self.ban))
		self.check_guilds.assert_not_awaited()
		self.bot.fetch_guild.assert_not_called()

	# ============================================================
	async def test_unfetchable_user_is_skipped(self) :
		self.bot.get_user.return_value = None
		self.bot.fetch_user = AsyncMock(side_effect=discord.NotFound(MagicMock(status=404), "gone"))
		self.assertFalse(await Bans().approve_ban(self.bot, self.ban))
		self.check_guilds.assert_not_awaited()
