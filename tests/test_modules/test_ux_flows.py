"""Tests for the setup, config, help and lookup UX changes.

A code-blind test run flagged these as confusing: no way to re-open setup, config replies posted for the
whole channel, True/False choices, an unreadable config-change log, a help pager that looked broken, a
Cross-ban button on a server's own ban, and a red read-only button. The automatic setup also created its
alerts channel readable by @everyone.
"""
import logging
import os
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import discord
from discord import app_commands

from classes.config.utils import ConfigUtils, format_change
from modules.Config import Config
from modules.Utility import Utility
from view.multiselect.ChannelSelect import ChannelSelect
from view.multiselect.RolesSelect import RolesSelect, alert_channel_overwrites
from test_permission_feedback import ALL_CHANNEL, make_channel, make_guild, make_interaction


class Quiet(unittest.IsolatedAsyncioTestCase) :
	def setUp(self) :
		logging.disable(logging.CRITICAL)
		self.addCleanup(logging.disable, logging.NOTSET)


class ConfigLogFormatTests(Quiet) :
	def test_channel_ids_become_mentions(self) :
		self.assertEqual(format_change("modchannel", 123), "• **Mod channel** → <#123>")

	def test_mentions_pass_through(self) :
		self.assertEqual(format_change("INVITE_CHANNEL", "<#5>"), "• **Invite channel** → <#5>")

	def test_removed_and_unknown_keys(self) :
		self.assertEqual(format_change("KICK_WARNINGS", None), "• **Kick warnings** → *removed*")

	def test_non_channel_numbers_stay_numbers(self) :
		self.assertEqual(format_change("BAN_WARNINGS", 3), "• **Ban warnings** → 3")

	async def test_log_has_no_code_block(self) :
		guild = make_guild()
		channel = make_channel(guild)
		with patch("classes.config.utils.ConfigData") as config, \
			patch("classes.config.utils.send_message", new=AsyncMock()) as send :
			config.return_value.get_toggle.return_value = True
			await ConfigUtils.log_change(guild, {"modchannel" : "<#10>"}, user_name="<@1>", channel=channel)
		text = send.call_args.args[1]
		self.assertNotIn("```", text)
		self.assertIn("**Mod channel** → <#10>", text)


class ConfigCommandTests(Quiet) :
	def setUp(self) :
		super().setUp()
		for target in ("ConfigData", "queue", "ConfigUtils", "ServerTransactions", "OnboardingLayout", "HelpLayout") :
			patcher = patch(f"modules.Config.{target}")
			setattr(self, target, patcher.start())
			self.addCleanup(patcher.stop)
		self.cog = Config(MagicMock())

	def sent(self, interaction) :
		return interaction.response.send_message.call_args.kwargs

	async def test_setup_opens_privately(self) :
		interaction = make_interaction(guild=make_guild())
		await Config.setup_command.callback(self.cog, interaction)
		self.assertTrue(self.sent(interaction)["ephemeral"])
		self.assertIs(self.sent(interaction)["view"], self.OnboardingLayout.return_value)

	async def test_help_is_private(self) :
		interaction = make_interaction(guild=make_guild())
		await Config.help.callback(self.cog, interaction)
		self.assertTrue(self.sent(interaction)["ephemeral"])

	async def test_appeals_uses_readable_choice(self) :
		interaction = make_interaction(guild=make_guild())
		await Config.appeals.callback(self.cog, interaction, app_commands.Choice(name="Don't allow appeals", value="no"))
		self.ConfigData.return_value.add_key.assert_called_once_with(1, "allow_appeals", False, overwrite=True)
		self.assertIn("not allowed", interaction.response.send_message.call_args.args[0])
		self.assertTrue(self.sent(interaction)["ephemeral"])

	async def test_visibility_uses_readable_choice(self) :
		interaction = make_interaction(guild=make_guild())
		await Config.visibility.callback(self.cog, interaction, app_commands.Choice(name="Hide our bans", value="yes"))
		self.ServerTransactions.return_value.update.assert_called_once_with(1, hidden=True)
		self.assertTrue(self.sent(interaction)["ephemeral"])

	async def test_change_success_is_private(self) :
		guild = make_guild()
		channel = make_channel(guild)
		interaction = make_interaction(guild=guild, channel=channel)
		await Config.change.callback(self.cog, interaction, app_commands.Choice(name="Mod Channel", value="modchannel"),
		                             channel)
		self.assertTrue(self.sent(interaction)["ephemeral"])

	def test_help_commands_are_distinct(self) :
		old = {"Are you stuck? This command will help you.", "Unsure of what a command does? Find it here!"}
		self.assertNotEqual(Config.help.description, Utility.help.description)
		self.assertFalse({Config.help.description, Utility.help.description} & old)


class SetupSelectTests(Quiet) :
	def test_alert_channel_is_private(self) :
		guild = make_guild()
		guild.default_role = MagicMock(name="everyone")
		staff = MagicMock(name="staff")
		overwrites = alert_channel_overwrites(guild, [staff, guild.default_role])
		self.assertFalse(overwrites[guild.default_role].view_channel)
		self.assertTrue(overwrites[staff].view_channel)
		self.assertTrue(overwrites[guild.me].send_messages)

	async def test_auto_setup_explains_missing_permissions(self) :
		guild = make_guild(dict(view_channel=True, send_messages=True, embed_links=True))
		guild.text_channels = []
		guild.create_text_channel = AsyncMock()
		interaction = make_interaction(guild=guild)
		with patch("view.multiselect.RolesSelect.ConfigTransactions") as config :
			await RolesSelect().callback(interaction)
		guild.create_text_channel.assert_not_awaited()
		config.return_value.config_unique_add.assert_not_called()
		self.assertIn("**Manage Channels**", interaction.response.send_message.call_args.args[0])

	async def test_manual_setup_refuses_unusable_channel(self) :
		guild = make_guild()
		channel = make_channel(guild, perms=dict(ALL_CHANNEL, view_channel=False, send_messages=False))
		guild.get_channel = MagicMock(return_value=channel)
		interaction = make_interaction(guild=guild)
		with patch("view.multiselect.ChannelSelect.ConfigTransactions") as config, \
			patch.object(ChannelSelect, "values", new_callable=PropertyMock, return_value=[channel]) :
			await ChannelSelect().callback(interaction)
		config.return_value.config_unique_add.assert_not_called()
		self.assertIn("**View Channel**, **Send Messages**", interaction.response.send_message.call_args.args[0])


def make_ban(gid, ban_id=1) :
	ban = MagicMock()
	ban.gid = gid
	ban.ban_id = ban_id
	ban.reason = "reason"
	ban.verified = False
	ban.message = 1
	ban.created_at = datetime(2026, 5, 25)
	ban.date_override = None
	ban.edited = None
	return ban


class LookupTests(Quiet) :
	def setUp(self) :
		super().setUp()
		for target, attr in (("view.buttons.lookup.ProofTransactions", "proof"),
		                     ("view.buttons.lookup.send_message", "send")) :
			patcher = patch(target, new=AsyncMock()) if attr == "send" else patch(target)
			setattr(self, attr, patcher.start())
			self.addCleanup(patcher.stop)
		from view.buttons.lookup import LookUp
		self.LookUp = LookUp

	async def run_lookup(self, bans, perms=None) :
		guild = make_guild()
		channel = make_channel(guild, perms=perms)
		bot = MagicMock()
		bot.get_guild = MagicMock(return_value=guild)
		interaction = make_interaction(guild=guild, channel=channel)
		interaction.edit_original_response = AsyncMock()
		view = self.LookUp(user_id=2)
		user = MagicMock()
		user.name, user.id = "target", 2
		await view.send_message(bot, channel, bans, user, interaction=interaction)
		return view, interaction

	async def test_cross_ban_hidden_for_own_bans(self) :
		view, _ = await self.run_lookup([make_ban(1)])
		self.assertNotIn(view.cross_ban, view.children)

	async def test_cross_ban_kept_for_other_servers(self) :
		view, _ = await self.run_lookup([make_ban(1), make_ban(99, 2)])
		self.assertIn(view.cross_ban, view.children)

	async def test_no_none_and_placeholder_resolved(self) :
		_, interaction = await self.run_lookup([make_ban(99)])
		embed = self.send.call_args.kwargs["embed"]
		self.assertNotIn("None", embed.fields[0].value)
		interaction.edit_original_response.assert_awaited_once()

	async def test_missing_permissions_replace_placeholder(self) :
		_, interaction = await self.run_lookup([make_ban(99)], perms=dict(ALL_CHANNEL, send_messages=False))
		content = interaction.edit_original_response.call_args.kwargs["content"]
		self.assertIn("**Send Messages**", content)
		self.assertIn("enable it,", content)
		self.send.assert_not_awaited()

	async def test_attach_files_is_not_required(self) :
		# The permission check calls Attach Files optional, so lookup must not refuse without it.
		await self.run_lookup([make_ban(99)], perms=dict(ALL_CHANNEL, attach_files=False))
		self.send.assert_awaited()

	# discord.py views need a running event loop, so the view tests are async.
	async def test_select_ban_excludes_own_server(self) :
		with patch("view.multiselect.selectban.BanTransactions") as bans :
			own, other = make_ban(1), make_ban(99, 2)
			other.guild.name = "Other server"
			bans.return_value.get_all_user.return_value = [own, other]
			from view.multiselect.selectban import SelectBan
			view = SelectBan(2, exclude_guild_id=1)
		self.assertEqual(view.bans, [other])


class HelpPagerTests(Quiet) :
	async def test_pager_names_the_command_range(self) :
		with patch("view.v2.HelpLayout.ServerTransactions"), patch.dict(os.environ, {"GUILD" : "1"}) :
			from view.v2.HelpLayout import HelpLayout
			layout = HelpLayout()
		layout.reasons = [discord.SelectOption(label=f"cmd{i}") for i in range(40)]
		layout.total_pages = 2
		layout._update_page()
		labels = [item.label for item in layout.buttonrow.children]
		self.assertIn("Commands 1–25 of 40", labels)
		self.assertIn("More commands ▶", labels)
		self.assertIn("commands 1–25 of 40", layout.selectrow.children[0].placeholder)
		self.assertIn("banwatch", str([b.url for b in layout.links.children]))


if __name__ == "__main__" :
	unittest.main()
