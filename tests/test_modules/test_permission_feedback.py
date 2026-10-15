"""Tests that a bot missing permissions always tells the user what is wrong, instead of failing silently.

A black-box run with the bot stripped of permissions found every failure path went quiet: errors were
posted with interaction.channel.send() (which needs the very permissions that were missing), the
permission check never answered, /config change named the wrong permission, /unban never answered
its interaction, and the welcome message was dropped when no channel was reachable. These tests pin
the fixes using Discord doubles; no live connection is needed.
"""
import logging
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from discord import app_commands
from discord_py_utilities.exceptions import NoPermissionException

from classes.onboarding import Onboarding
from classes.permissions import PermissionsCheck, channel_problems
from classes.replies import reply
from modules import logs
from classes.permissions_notice import PermissionNotice
from modules.Config import Config
from modules.Invite import Invite
from modules.MemberLookup import MemberLookup
from modules.Tools import Tools

ALL_GUILD = dict(ban_members=True, view_audit_log=True, kick_members=True, manage_messages=True,
                 manage_guild=True, create_instant_invite=True)
ALL_CHANNEL = dict(view_channel=True, send_messages=True, embed_links=True, attach_files=True,
                   read_message_history=True)


def make_guild(guild_perms=None, role_name="General Test Bot") :
	guild = MagicMock(spec=discord.Guild)
	guild.id = 1
	guild.name = "Test server with a very long name"
	guild.me = MagicMock()
	guild.me.guild_permissions = discord.Permissions(**(ALL_GUILD if guild_perms is None else guild_perms))
	guild.self_role = MagicMock()
	guild.self_role.name = role_name
	guild.self_role.is_default.return_value = False
	return guild


def make_channel(guild, perms=None, name="moderator-only", channel_id=10) :
	channel = MagicMock(spec=discord.TextChannel)
	channel.id = channel_id
	channel.name = name
	channel.mention = f"<#{channel_id}>"
	channel.guild = guild
	channel.permissions_for = MagicMock(return_value=discord.Permissions(**(ALL_CHANNEL if perms is None else perms)))
	channel.send = AsyncMock()
	return channel


def make_interaction(guild=None, channel=None, done=False) :
	interaction = MagicMock()
	interaction.guild = guild
	interaction.channel = channel
	interaction.response.is_done = MagicMock(return_value=done)
	interaction.response.send_message = AsyncMock()
	interaction.followup.send = AsyncMock()
	return interaction


def http_error(cls, status) :
	response = MagicMock()
	response.status = status
	response.reason = "error"
	return cls(response, "error")


class Quiet(unittest.IsolatedAsyncioTestCase) :
	def setUp(self) :
		logging.disable(logging.CRITICAL)
		self.addCleanup(logging.disable, logging.NOTSET)


class ReplyTests(Quiet) :
	async def test_uses_initial_response_when_open(self) :
		interaction = make_interaction()
		self.assertTrue(await reply(interaction, "hi"))
		interaction.response.send_message.assert_awaited_once_with(content="hi", ephemeral=True)
		interaction.followup.send.assert_not_awaited()

	async def test_uses_followup_when_already_responded(self) :
		interaction = make_interaction(done=True)
		await reply(interaction, "hi")
		interaction.followup.send.assert_awaited_once_with(content="hi", ephemeral=True)

	async def test_falls_back_to_channel_when_interaction_fails(self) :
		channel = make_channel(make_guild())
		interaction = make_interaction(channel=channel)
		interaction.response.send_message.side_effect = http_error(discord.NotFound, 404)
		self.assertTrue(await reply(interaction, "hi"))
		channel.send.assert_awaited_once_with("hi")

	async def test_never_raises_when_everything_fails(self) :
		channel = make_channel(make_guild())
		channel.send.side_effect = http_error(discord.Forbidden, 403)
		interaction = make_interaction(channel=channel)
		interaction.response.send_message.side_effect = http_error(discord.NotFound, 404)
		self.assertFalse(await reply(interaction, "hi"))


class ErrorMessageTests(Quiet) :
	def test_bot_missing_permissions_names_permission_and_role(self) :
		interaction = make_interaction(guild=make_guild())
		msg = logs._expected_app_error_message(app_commands.BotMissingPermissions(["ban_members"]), None, interaction)
		self.assertIn("**Ban Members**", msg)
		self.assertIn("General Test Bot", msg)
		self.assertIn("I'm missing", msg)

	def test_user_missing_permissions_is_about_the_user(self) :
		msg = logs._expected_app_error_message(app_commands.MissingPermissions(["manage_guild"]), None)
		self.assertIn("You need **Manage Server**", msg)

	def test_plain_check_failure(self) :
		msg = logs._expected_app_error_message(app_commands.CheckFailure(), None)
		self.assertIn("do not have permission", msg)

	def test_no_permission_exception_is_humanized(self) :
		guild = make_guild()
		channel = make_channel(guild, perms=dict(ALL_CHANNEL, view_channel=False, send_messages=False))
		exc = NoPermissionException(required_perms=["view_channel", "send_messages", "embed_links"], channel=channel)
		msg = logs._expected_app_error_message(app_commands.AppCommandError(), exc)
		self.assertIn("**View Channel**, **Send Messages**", msg)
		self.assertNotIn("view_channel", msg)

	def test_forbidden_mentions_channel_gap_without_blaming_it(self) :
		# A 403 doesn't say which permission was missing: /export_bans failing on Ban Members was once
		# reported as a channel-permission problem.
		guild = make_guild()
		channel = make_channel(guild, perms=dict(ALL_CHANNEL, send_messages=False))
		interaction = make_interaction(guild=guild, channel=channel)
		msg = logs._expected_app_error_message(app_commands.AppCommandError(), http_error(discord.Forbidden, 403),
		                                       interaction)
		self.assertTrue(msg.startswith("❌ Discord blocked this action"))
		self.assertIn("also missing **Send Messages**", msg)
		self.assertIn("/config permissioncheck", msg)

	def test_server_only_permission_has_no_channel_route(self) :
		interaction = make_interaction(guild=make_guild())
		msg = logs._expected_app_error_message(app_commands.BotMissingPermissions(["ban_members"]), None, interaction)
		self.assertNotIn("channel's permissions", msg)

	def test_channel_permission_keeps_channel_route(self) :
		interaction = make_interaction(guild=make_guild())
		msg = logs._expected_app_error_message(app_commands.BotMissingPermissions(["attach_files"]), None, interaction)
		self.assertIn("channel's permissions", msg)

	def test_forbidden_without_channel_gap_points_to_permissioncheck(self) :
		guild = make_guild()
		interaction = make_interaction(guild=guild, channel=make_channel(guild))
		msg = logs._expected_app_error_message(app_commands.AppCommandError(), http_error(discord.Forbidden, 403),
		                                       interaction)
		self.assertIn("/config permissioncheck", msg)
		self.assertNotIn("assign", msg)

	async def test_handler_replies_to_interaction_not_channel(self) :
		guild = make_guild()
		channel = make_channel(guild, perms={})
		channel.send.side_effect = http_error(discord.Forbidden, 403)
		interaction = make_interaction(guild=guild, channel=channel)
		await logs.Logging(MagicMock()).on_app_command_error(interaction, app_commands.BotMissingPermissions(["ban_members"]))
		interaction.response.send_message.assert_awaited_once()
		kwargs = interaction.response.send_message.call_args.kwargs
		self.assertTrue(kwargs["ephemeral"])
		self.assertIn("Ban Members", kwargs["content"])
		channel.send.assert_not_awaited()


class PermissionReportTests(Quiet) :
	def field(self, embed, prefix) :
		return next(f for f in embed.fields if f.name.startswith(prefix))

	def test_everything_granted_is_green(self) :
		guild = make_guild()
		mod = make_channel(guild)
		embed = PermissionsCheck.build_report(guild, mod, mod)
		self.assertEqual(embed.colour, discord.Colour.green())
		self.assertFalse(any(f.name == "How to fix" for f in embed.fields))

	def test_missing_required_guild_permission_is_red(self) :
		guild = make_guild(dict(ALL_GUILD, ban_members=False))
		embed = PermissionsCheck.build_report(guild, make_channel(guild))
		self.assertEqual(embed.colour, discord.Colour.red())
		self.assertIn("❌ **Ban Members**", self.field(embed, "Required").value)
		self.assertIn("General Test Bot", self.field(embed, "How to fix").value)

	def test_missing_optional_only_is_orange(self) :
		guild = make_guild(dict(ALL_GUILD, kick_members=False))
		embed = PermissionsCheck.build_report(guild, make_channel(guild))
		self.assertEqual(embed.colour, discord.Colour.orange())

	def test_no_mod_channel_is_reported(self) :
		guild = make_guild()
		embed = PermissionsCheck.build_report(guild, None)
		self.assertEqual(embed.colour, discord.Colour.red())
		self.assertIn("Not set", self.field(embed, "Mod channel").value)

	def test_mod_channel_missing_one_permission_is_not_ok(self) :
		# The old check passed with one permission missing (len(missing) <= 1).
		guild = make_guild()
		mod = make_channel(guild, perms=dict(ALL_CHANNEL, view_channel=False))
		embed = PermissionsCheck.build_report(guild, mod)
		self.assertEqual(embed.colour, discord.Colour.red())
		self.assertIn("❌ **View Channel**", self.field(embed, "Mod channel").value)

	def test_current_channel_listed_separately(self) :
		guild = make_guild()
		mod = make_channel(guild)
		here = make_channel(guild, perms=dict(ALL_CHANNEL, send_messages=False), name="rules", channel_id=11)
		embed = PermissionsCheck.build_report(guild, mod, here)
		self.assertIn("❌ **Send Messages**", self.field(embed, "This channel: #rules").value)

	async def test_permission_check_replies_privately(self) :
		guild = make_guild()
		channel = make_channel(guild, perms={})
		interaction = make_interaction(guild=guild, channel=channel)
		await PermissionsCheck().permission_check(interaction, mod_channel=make_channel(guild))
		kwargs = interaction.response.send_message.call_args.kwargs
		self.assertTrue(kwargs["ephemeral"])
		self.assertIsInstance(kwargs["embed"], discord.Embed)
		channel.send.assert_not_awaited()


class ConfigChangeTests(Quiet) :
	def setUp(self) :
		super().setUp()
		for target in ("ConfigData", "queue", "ConfigUtils") :
			patcher = patch(f"modules.Config.{target}")
			setattr(self, target, patcher.start())
			self.addCleanup(patcher.stop)

	async def run_change(self, channel, guild) :
		interaction = make_interaction(guild=guild, channel=channel)
		option = app_commands.Choice(name="Mod Channel", value="modchannel")
		await Config.change.callback(Config(MagicMock()), interaction, option, channel)
		return interaction.response.send_message.call_args

	def test_channel_problems_reports_view_channel_first(self) :
		guild = make_guild()
		channel = make_channel(guild, perms=dict(ALL_CHANNEL, view_channel=False, send_messages=False))
		required, _ = channel_problems(channel)
		self.assertEqual(required, ["view_channel", "send_messages"])

	async def test_names_every_missing_permission_privately(self) :
		guild = make_guild()
		channel = make_channel(guild, perms=dict(ALL_CHANNEL, view_channel=False, send_messages=False))
		call = await self.run_change(channel, guild)
		self.assertIn("**View Channel**, **Send Messages**", call.args[0])
		self.assertTrue(call.kwargs["ephemeral"])
		self.ConfigData.return_value.add_key.assert_not_called()

	async def test_saves_and_warns_about_optional_and_ban_permissions(self) :
		guild = make_guild(dict(ALL_GUILD, ban_members=False))
		channel = make_channel(guild, perms=dict(ALL_CHANNEL, attach_files=False))
		call = await self.run_change(channel, guild)
		self.ConfigData.return_value.add_key.assert_called_once()
		self.assertIn("**Attach Files**", call.args[0])
		self.assertIn("**Ban Members**", call.args[0])


class UnbanTests(Quiet) :
	async def run_unban(self, side_effect=None) :
		guild = make_guild()
		guild.unban = AsyncMock(side_effect=side_effect)
		channel = make_channel(guild)
		interaction = make_interaction(guild=guild, channel=channel)
		user = MagicMock(spec=discord.User)
		user.name = "target"
		user.mention = "<@2>"
		await Tools.unban.callback(Tools(MagicMock()), interaction, user)
		return interaction, channel

	async def test_success_answers_interaction(self) :
		interaction, channel = await self.run_unban()
		kwargs = interaction.response.send_message.call_args.kwargs
		self.assertFalse(kwargs["ephemeral"])
		self.assertIn("unbanned", kwargs["embed"].title)
		channel.send.assert_not_awaited()

	async def test_not_banned_answers_interaction(self) :
		interaction, channel = await self.run_unban(http_error(discord.NotFound, 404))
		self.assertIn("not banned", interaction.response.send_message.call_args.kwargs["content"])
		channel.send.assert_not_awaited()

	def test_checks_bot_ban_permission(self) :
		# A user check alone let the command reach guild.unban and fail with a generic 403.
		for command in (Tools.unban, Tools.mass_unban, Tools.export_bans) :
			self.assertTrue(any("bot_has_permissions" in getattr(c, "__qualname__", "") for c in command.checks),
			                command.name)

	async def test_export_bans_builds_file_in_memory(self) :
		guild = make_guild()

		async def bans() :
			entry = MagicMock()
			entry.user = MagicMock(id=5)
			entry.user.__str__ = lambda self : "someone"
			entry.reason = None
			yield entry

		guild.bans = bans
		interaction = make_interaction(guild=guild)
		interaction.response.defer = AsyncMock()
		with patch("modules.Tools.discord.File") as file, patch("builtins.open") as opened :
			await Tools.export_bans.callback(Tools(MagicMock()), interaction)
		opened.assert_not_called()
		self.assertEqual(file.call_args.args[0].getvalue(), b"User: someone (ID: 5) - Reason: No reason provided\n")
		self.assertTrue(interaction.followup.send.call_args.kwargs["ephemeral"])


class OnboardingTests(Quiet) :
	def setUp(self) :
		super().setUp()
		patcher = patch("classes.onboarding.OnboardingLayout")
		patcher.start()
		self.addCleanup(patcher.stop)

	async def test_posts_in_accessible_channel(self) :
		guild = make_guild()
		channel = make_channel(guild)
		guild.owner = MagicMock()
		guild.owner.send = AsyncMock()
		with patch("classes.onboarding.find_first_accessible_text_channel", return_value=channel) :
			self.assertTrue(await Onboarding.deliver_join_message(guild))
		channel.send.assert_awaited_once()
		guild.owner.send.assert_not_awaited()

	async def test_dms_owner_with_reason_when_no_channel(self) :
		guild = make_guild()
		guild.owner = MagicMock()
		guild.owner.send = AsyncMock()
		with patch("classes.onboarding.find_first_accessible_text_channel", return_value=None) :
			self.assertTrue(await Onboarding.deliver_join_message(guild))
		self.assertEqual(guild.owner.send.await_count, 2)
		self.assertIn("couldn't post this welcome message", guild.owner.send.call_args.args[0])

	async def test_dms_owner_when_channel_send_fails(self) :
		guild = make_guild()
		channel = make_channel(guild)
		channel.send.side_effect = http_error(discord.Forbidden, 403)
		guild.owner = MagicMock()
		guild.owner.send = AsyncMock()
		with patch("classes.onboarding.find_first_accessible_text_channel", return_value=channel) :
			self.assertTrue(await Onboarding.deliver_join_message(guild))
		guild.owner.send.assert_awaited()

	async def test_closed_owner_dms_do_not_raise(self) :
		guild = make_guild()
		guild.owner = MagicMock()
		guild.owner.send = AsyncMock(side_effect=http_error(discord.Forbidden, 403))
		with patch("classes.onboarding.find_first_accessible_text_channel", return_value=None) :
			self.assertFalse(await Onboarding.deliver_join_message(guild))


class NoticeRoleNameTests(Quiet) :
	def test_notice_names_the_real_bot_role(self) :
		guild = make_guild()
		guild.icon = None
		channel = make_channel(guild)
		embed = PermissionNotice.build_embed(guild, channel=channel, missing=["ban_members"])
		steps = next(f for f in embed.fields if f.name == "How to fix").value
		self.assertIn("General Test Bot", steps)
		self.assertNotIn("**Banwatch**", steps)


class UnexpectedErrorTests(Quiet) :
	async def test_notice_hides_internals_and_points_to_support(self) :
		cog = logs.Logging(MagicMock())
		cog._capture = MagicMock(return_value="abc123")
		cog._notify_dev = AsyncMock()
		interaction = make_interaction(guild=make_guild())
		await cog.on_app_command_error(interaction, app_commands.AppCommandError("KeyError: 'secret_internal'"))
		content = interaction.response.send_message.call_args.kwargs["content"]
		self.assertNotIn("secret_internal", content)
		self.assertNotIn("Rico", content)
		self.assertIn("/support bug", content)
		self.assertIn("abc123", content)


class InviteChannelTests(Quiet) :
	def setUp(self) :
		super().setUp()
		for target in ("ConfigTransactions", "ConfigData", "ServerTransactions", "queue", "ConfigUtils", "Bans") :
			patcher = patch(f"modules.Invite.{target}")
			setattr(self, target, patcher.start())
			self.addCleanup(patcher.stop)
		self.Bans.return_value.create_invite = AsyncMock(return_value="https://discord.gg/test")

	async def run_set_channel(self, bot_perms, everyone_can_view=True) :
		guild = make_guild()
		guild.default_role = object()
		channel = make_channel(guild)
		channel.permissions_for = MagicMock(side_effect=lambda target : discord.Permissions(
			view_channel=everyone_can_view) if target is guild.default_role else discord.Permissions(**bot_perms))
		interaction = make_interaction(guild=guild, channel=channel)
		await Invite.set_channel.callback(Invite(MagicMock()), interaction, channel)
		return interaction.response.send_message.call_args

	async def test_refuses_channel_without_invite_permission(self) :
		call = await self.run_set_channel(dict(view_channel=True, create_instant_invite=False))
		self.assertIn("**Create Invite**", call.args[0])
		self.assertTrue(call.kwargs["ephemeral"])
		self.ConfigTransactions.return_value.config_unique_add.assert_not_called()

	async def test_warns_when_channel_is_hidden_from_everyone(self) :
		call = await self.run_set_channel(dict(view_channel=True, create_instant_invite=True), everyone_can_view=False)
		self.assertIn("hidden from @everyone", call.args[0])
		self.ConfigTransactions.return_value.config_unique_add.assert_called_once()

	async def test_public_channel_has_no_warning(self) :
		call = await self.run_set_channel(dict(view_channel=True, create_instant_invite=True))
		self.assertNotIn("⚠️", call.args[0])


class OptionDescriptionTests(unittest.TestCase) :
	def test_admin_commands_describe_every_option(self) :
		for command in (Config.change, Config.appeals, Config.visibility, Config.toggles, MemberLookup.lookup) :
			for param in command.parameters :
				self.assertNotEqual(param.description, "…", f"/{command.qualified_name} {param.name} has no description")


if __name__ == "__main__" :
	unittest.main()
