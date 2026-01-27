import logging

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from discord_py_utilities.messages import send_message, send_response
from discord_py_utilities.permissions import check_missing_channel_permissions, get_bot_permissions

from classes.configdata import ConfigData
from database.transactions.ServerTransactions import ServerTransactions


class Config(commands.GroupCog, name="config") :
	"""
	Configure Banwatch for your server. Set channels, toggle features, and check permissions.
	"""

	def __init__(self, bot: commands.Bot) :
		self.bot = bot

	@app_commands.command(name="change", description="Set the channel for bot announcements and moderation logs.")
	@app_commands.choices(option=[
		Choice(name="Mod channel", value="mod"),
	])
	@app_commands.checks.has_permissions(manage_guild=True)
	@app_commands.guild_only()
	async def change(self, interaction: discord.Interaction, option: Choice[str], channel: discord.TextChannel) :
		"""
		Changes server-specific settings for Banwatch.

		**Permissions:**
		- `Manage Server`
		"""
		if option.value == "mod" :
			if not channel.permissions_for(interaction.guild.me).send_messages :
				return await send_response(interaction, f"❌ I need the `Send Messages` permission in {channel.mention} to set it as the mod channel.")
			if not channel.permissions_for(interaction.guild.me).view_channel :
				return await send_response(interaction, f"❌ I need the `Read Messages` permission in {channel.mention} to set it as the mod channel.")
			ConfigData().add_key(interaction.guild.id, "modchannel", channel.id, overwrite=True)
		await send_response(interaction, f"Set {option.name} to {channel.mention}")

	@app_commands.command(name="appeals", description="Enable or disable the ability for users to appeal bans.")
	@app_commands.checks.has_permissions(manage_guild=True)
	@app_commands.guild_only()
	async def appeals(self, interaction: discord.Interaction, allow: bool) :
		"""
		Enables or disables the ban appeal system for this server.

		**Permissions:**
		- `Manage Server`
		"""
		ConfigData().add_key(interaction.guild.id, "allow_appeals", allow, overwrite=True)
		await send_response(interaction, f"Ban appeals have been set to: {'enabled' if allow is True else 'disabled'}")

	@app_commands.command(name="visibility", description="Hide your server's bans from showing up in public lookups.")
	@app_commands.checks.has_permissions(manage_guild=True)
	@app_commands.guild_only()
	async def visibility(self, interaction: discord.Interaction, hide: bool) :
		"""
		Toggles whether this server's bans are visible in public lookups.

		**Permissions:**
		- `Manage Server`
		"""
		ServerTransactions().update(interaction.guild.id, hidden=hide)
		await send_response(interaction,
		                    f"Your server's visibility has ben set to: {'hidden' if hide is True else 'Visible'}\n\n"
		                    f"Your bans may temporarily still be available in the checkall cache, which is reloaded every 10 minutes")

	@app_commands.command(name="permission_check",
	                      description="Checks if the bot has all necessary permissions to function correctly.")
	@app_commands.guild_only()
	async def permissioncheck(self, interaction: discord.Interaction) :
		"""
		Checks if the bot has the required permissions in the current channel and server. This is the first step in troubleshooting if the bot is not functioning as expected. Please run this command before contacting support.

		**Permissions:**
		- None required for the user.
		"""
		await send_response(interaction, "⌛ Checking permissions...", ephemeral=True)
		permissions = {
			"Ban Members"       : interaction.guild.me.guild_permissions.ban_members,
			"Kick Members"      : interaction.guild.me.guild_permissions.kick_members,
			"Manage Guild"      : interaction.guild.me.guild_permissions.manage_guild,
			"Create Invite"     : interaction.guild.me.guild_permissions.create_instant_invite,
			"Embedded Activities": interaction.guild.me.guild_permissions.use_embedded_activities,
			"View Audit Log"    : interaction.guild.me.guild_permissions.view_audit_log,
			"Manage Messages"   : interaction.guild.me.guild_permissions.manage_messages,
			"Send Messages"     : interaction.guild.me.guild_permissions.send_messages,
			"Attach Files"      : interaction.guild.me.guild_permissions.attach_files,
		}
		missing = check_missing_channel_permissions(interaction.channel,
		                                            ['view_channel', 'send_messages', 'embed_links', 'attach_files'])
		permission_status = {
			"Ban_members"               : "✅" if "ban_members" in permissions else "❌",
			"Kick_members"              : "✅" if "kick_members" in permissions else "❌",
			"Manage_guild"              : "✅" if "manage_guild" in permissions else "❌",
			"Create_instant_invite"     : "✅" if "create_instant_invite" in permissions else "❌",
			"Use_embedded_activities"   : "✅" if "use_embedded_activities" in permissions else "❌",
			"View_audit_log"            : "✅" if "view_audit_log" in permissions else "❌",
			"Manage_messages"           : "✅" if "manage_messages" in permissions else "❌",
			"Send_messages"             : "✅" if "send_messages" in permissions else "❌",
			"Attach_files"              : "✅" if "attach_files" in permissions else "❌",
			"Can message in modchannel" : "✅" if len(missing) <= 1 else "❌",
		}
		embed = discord.Embed(title="Permissions Check", color=0x00ff00)
		embed.description = f"I have the following permissions in {interaction.guild.name}::"
		for key, value in permission_status.items() :
			embed.add_field(name=key, value=value, inline=False)
		await send_message(interaction.user, embed=embed)




async def setup(bot: commands.Bot) :
	await bot.add_cog(Config(bot))
