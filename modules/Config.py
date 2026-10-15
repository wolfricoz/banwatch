import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from discord_py_utilities.messages import send_response
from discord_py_utilities.permissions import check_missing_guild_permissions

from classes.config.utils import ConfigUtils
from classes.configdata import ConfigData
from classes.permissions import PermissionsCheck, channel_problems
from classes.permissions_notice import bot_role_name, format_permissions
from classes.queue import queue
from data.config.mappings import Channels, available_toggles
from database.transactions.ServerTransactions import ServerTransactions
from view.v2.HelpLayout import HelpLayout
from view.v2.OnboardingLayout import OnboardingLayout


class Config(commands.GroupCog, name="config") :
	"""
	Configure Banwatch for your server. Set channels, toggle features, and check permissions.
	"""

	def __init__(self, bot: commands.Bot) :
		self.bot = bot

	# ============================================================
	@app_commands.command(name="help", description="Banwatch setup guide: what to configure and which permissions I need.")
	async def help(self, interaction: discord.Interaction) :
		"""
				If you're feeling stuck or need assistance with configuring the bot, this command will provide you with helpful information and guidance.

		"""
		await send_response(interaction, " ", view=HelpLayout(), ephemeral=True)

	# ============================================================
	@app_commands.command(name="setup", description="Guided setup: pick or create the mod channel, then check my permissions.")
	@app_commands.checks.has_permissions(manage_guild=True)
	@app_commands.guild_only()
	async def setup_command(self, interaction: discord.Interaction) :
		"""
		Opens the same guided setup as the welcome message: create a mod channel automatically or pick an existing
		one, after which Banwatch checks its permissions there and tells you what is missing.

		**Permissions:**
		- `Manage Server`
		"""
		await send_response(interaction, " ", view=OnboardingLayout(), ephemeral=True)

	# ============================================================
	@app_commands.command(name="change", description="Set the channel for bot announcements and moderation logs.")
	@app_commands.choices(option=[
		Choice(name=c.name.replace("_", " ").title(), value=c.value) for c in Channels
	])
	@app_commands.describe(option="Which channel setting to change.",
	                       channel="The channel to use; I need View Channel, Send Messages and Embed Links there.")
	@app_commands.checks.has_permissions(manage_guild=True)
	@app_commands.guild_only()
	async def change(self, interaction: discord.Interaction, option: Choice[str], channel: discord.TextChannel) :
		"""
		Changes server-specific settings for Banwatch.

		**Permissions:**
		- `Manage Server`
		"""
		# Report every missing permission at once: checking one at a time sent admins to grant
		# Send Messages when View Channel was the real blocker (Send Messages reads as missing without it).
		missing_required, missing_optional = channel_problems(channel)
		role = bot_role_name(interaction.guild)
		if missing_required :
			return await send_response(
				interaction,
				f"❌ I can't use {channel.mention} as the {option.name} yet: I'm missing "
				f"{format_permissions(missing_required)} there.\n"
				f"Open {channel.mention} → **Edit Channel → Permissions**, add **{role}**, enable those, "
				"then run this command again.",
				ephemeral=True)

		ConfigData().add_key(interaction.guild.id, option.value, channel.id, overwrite=True)
		queue().add(ConfigUtils.log_change(interaction.guild, {option.value : channel.mention},
		                                   user_name=interaction.user.mention))
		warnings = []
		if missing_optional :
			warnings.append(f"⚠️ I'm also missing {format_permissions(missing_optional)} in {channel.mention}; "
			                "some features won't work there until they're enabled.")
		message = f"Set **{option.name}** to {channel.mention}."
		if option.value == Channels.MOD_CHANNEL :
			message += ("\n\nIf this is your first mod channel, Banwatch will now import your server's existing bans. "
			            "Bans that need evidence will get a request in this channel, "
			            "__**so expect a burst of messages there.**__")
			if missing_ban := check_missing_guild_permissions(interaction.guild, ["ban_members"]) :
				warnings.append(f"⚠️ I'm missing {format_permissions(missing_ban)} server-wide, so I can't read "
				                f"your bans to import them. Enable it under **Server Settings → Roles → {role}**.")
		if warnings :
			message += "\n\n" + "\n".join(warnings)
		# Private: the config-change log already tells the rest of the team in the mod channel.
		await send_response(interaction, message, ephemeral=True)

	# ============================================================
	@app_commands.command(name="appeals", description="Enable or disable the ability for users to appeal bans.")
	@app_commands.choices(allow=[Choice(name="Allow appeals", value="yes"), Choice(name="Don't allow appeals", value="no")])
	@app_commands.describe(allow="Whether people banned from this server can appeal their ban.")
	@app_commands.checks.has_permissions(manage_guild=True)
	@app_commands.guild_only()
	async def appeals(self, interaction: discord.Interaction, allow: Choice[str]) :
		"""
		Enables or disables the ban appeal system for this server.

		**Permissions:**
		- `Manage Server`
		"""
		allow = allow.value == "yes"
		ConfigData().add_key(interaction.guild.id, "allow_appeals", allow, overwrite=True)
		queue().add(ConfigUtils.log_change(interaction.guild,
		                                   {"allow_appeals" : "ENABLED" if allow is True else "DISABLED"},
		                                   user_name=interaction.user.mention))
		await send_response(interaction, f"Ban appeals are now **{'allowed' if allow else 'not allowed'}**.", ephemeral=True)

	# ============================================================
	@app_commands.command(name="visibility", description="Hide your server's bans from showing up in public lookups.")
	@app_commands.choices(hide=[Choice(name="Hide our bans", value="yes"), Choice(name="Show our bans", value="no")])
	@app_commands.describe(hide="Whether your server's bans show up in other servers' lookups.")
	@app_commands.checks.has_permissions(manage_guild=True)
	@app_commands.guild_only()
	async def visibility(self, interaction: discord.Interaction, hide: Choice[str]) :
		"""
		Toggles whether this server's bans are visible in public lookups.

		**Permissions:**
		- `Manage Server`
		"""
		hide = hide.value == "yes"
		ServerTransactions().update(interaction.guild.id, hidden=hide)
		queue().add(ConfigUtils.log_change(interaction.guild,
		                                   {"visibility" : "hidden" if hide is True else "visible"},
		                                   user_name=interaction.user.mention))
		await send_response(interaction,
		                    f"Your server's visibility has been set to: {'hidden' if hide is True else 'Visible'}\n\n"
		                    f"Your bans may temporarily still be available in the checkall cache, which is reloaded every 10 minutes",
		                    ephemeral=True)

	# ============================================================
	@app_commands.command(name="toggles", description="Enable or disable optional Banwatch behaviour for this server.")
	@app_commands.choices(action=[Choice(name=x, value=x) for x in ["enabled", "disabled"]],
	                      key=[Choice(name=x, value=x) for x in available_toggles])
	@app_commands.describe(key="The optional behaviour to change; see /config help for what each one does.",
	                       action="Turn it on or off.")
	@app_commands.checks.has_permissions(manage_guild=True)
	@app_commands.guild_only()
	async def toggles(self, interaction: discord.Interaction, key: Choice[str], action: Choice[str]) :
		"""
		Turns one of Banwatch's optional behaviours on or off. See /config help for what each one does.

		**Permissions:**
		- `Manage Server`
		"""
		ConfigData().add_key(interaction.guild.id, key.value, action.value.upper(), overwrite=True)
		queue().add(ConfigUtils.log_change(interaction.guild, {key.value : action.value.upper()},
		                                   user_name=interaction.user.mention))
		return await send_response(interaction, f"{key.value} has been set to {action.value}", ephemeral=True)

	# ============================================================
	@app_commands.command(name="permissioncheck",
	                      description="Checks if the bot has all necessary permissions to function correctly.")
	@app_commands.guild_only()
	async def permissioncheck(self, interaction: discord.Interaction) :
		"""
		Checks if the bot has the required permissions in the current channel and server. This is the first step in troubleshooting if the bot is not functioning as expected. Please run this command before contacting support.

		**Permissions:**
		- None required for the user.
		"""
		await PermissionsCheck().permission_check(interaction)





async def setup(bot: commands.Bot) :
	await bot.add_cog(Config(bot))
