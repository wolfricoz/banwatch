import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from discord_py_utilities.exceptions import NoPermissionException
from discord_py_utilities.messages import send_message, send_response

from classes.configdata import ConfigData
from database.databaseController import ServerDbTransactions
from discord_py_utilities.permissions import check_missing_channel_permissions, get_bot_permissions


class config(commands.GroupCog, name="config") :

	def __init__(self, bot: commands.Bot) :
		self.bot = bot

	@app_commands.command(name="change", description="[CONFIG COMMAND] Sets up the channels for the bot.")
	@app_commands.choices(option=[
		Choice(name="Mod channel", value="mod"),
	])
	@app_commands.checks.has_permissions(manage_guild=True)
	async def crole(self, interaction: discord.Interaction, option: Choice[str], channel: discord.TextChannel) :
		match option.value :
			case "mod" :
				ConfigData().add_key(interaction.guild.id, "modchannel", channel.id, overwrite=True)
		await send_response(interaction, f"Set {option.name} to {channel.mention}")

	@app_commands.command(name="appeals", description="[CONFIG COMMAND] turn on/off ban appeals")
	@app_commands.checks.has_permissions(manage_guild=True)
	async def appeals(self, interaction: discord.Interaction, allow: bool) :
		await interaction.response.defer(ephemeral=True)
		ConfigData().add_key(interaction.guild.id, "allow_appeals", allow)

	@app_commands.command(name="visibility", description="[Config Command] Allows you to hide all bans from banwatch")
	@app_commands.checks.has_permissions(manage_guild=True)
	async def visibility(self, interaction: discord.Interaction, hide: bool) :
		ServerDbTransactions().update(interaction.guild.id, hidden=hide)
		await send_response(interaction,
		                    f"Your server's visibility has ben set to: {'hidden' if hide is True else 'Visible'}\n\n"
		                    f"Your bans may temporarily still be available in the checkall cache, which is reloaded every 10 minutes")

	@app_commands.command(name="permission_check", description="Checks if the bot has the required permissions. Responds in DM.")
	async def permissioncheck(self, interaction: discord.Interaction) :
		await send_response(interaction, "⌛ Checking permissions...", ephemeral=True)
		modchannel = self.bot.get_channel(ConfigData().get_key(interaction.guild.id, "modchannel"))
		if modchannel is None :
			return await send_response(interaction, "❌ Mod channel not set. Please set it using `/config change`")
		missing = check_missing_channel_permissions(modchannel,
		                                            ['view_channel', 'send_messages', 'embed_links', 'attach_files'])
		permissions = get_bot_permissions(interaction.guild)
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
	await bot.add_cog(config(bot))
