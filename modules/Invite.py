import discord
from discord import app_commands
from discord.ext.commands import Bot, GroupCog
from discord_py_utilities.messages import send_response
from discord_py_utilities.permissions import check_missing_channel_permissions

from classes.bans import Bans
from classes.config.utils import ConfigUtils
from classes.configdata import ConfigData
from classes.permissions_notice import bot_role_name, format_permissions
from classes.queue import queue
from data.config.mappings import Channels
from database.transactions.ConfigTransactions import ConfigTransactions
from database.transactions.ServerTransactions import ServerTransactions

# The bot can only create an invite for a channel it can see and has Create Invite in.
INVITE_CHANNEL_PERMS = ["view_channel", "create_instant_invite"]


class Invite(GroupCog, name="invite", description="Manage your servers invites!") :
	"""

	"""

	def __init__(self, bot: Bot) :
		self.bot = bot

	# ============================================================
	@app_commands.command(name="set_channel", description="Sets the channel where the invite gets created.")
	@app_commands.guild_only()
	@app_commands.checks.has_permissions(manage_channels=True)
	async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
		"""
		Allows you to set the channel where the invite gets created.

		Permissions:
		- manage_channels
		"""
		# Without these the invite silently falls back to another channel, so the reply would name the wrong one.
		if missing := check_missing_channel_permissions(channel, INVITE_CHANNEL_PERMS) :
			return await send_response(
				interaction,
				f"❌ I can't create an invite for {channel.mention}: I'm missing {format_permissions(missing)} there.\n"
				f"Open {channel.mention} → **Edit Channel → Permissions**, add **{bot_role_name(interaction.guild)}**, "
				"enable those, then run this command again.",
				ephemeral=True)

		ConfigTransactions().config_unique_add(interaction.guild.id, Channels.INVITE, channel.id)
		ConfigData().load_guild(interaction.guild.id)
		invite = await Bans().create_invite(self.bot, interaction.guild, force_new=True)
		ServerTransactions().update(interaction.guild.id, invite=invite)
		queue().add(ConfigUtils.log_change(interaction.guild, {Channels.INVITE : channel.mention},
		                                   user_name=interaction.user.mention))
		message = f"You've changed your invite channel to {channel.mention}, here's your new invite: {invite}"
		if not channel.permissions_for(interaction.guild.default_role).view_channel :
			message += (f"\n\n⚠️ {channel.mention} is hidden from @everyone, so people joining through this invite "
			            "won't be able to see it. A public channel such as your rules or welcome channel works best.")
		await send_response(interaction, message)

	# ============================================================
	@app_commands.command(name="regenerate", description="Generates a new invite!")
	@app_commands.guild_only()
	@app_commands.checks.has_permissions(manage_channels=True)
	async def regenerate(self, interaction: discord.Interaction):
		"""
		Creates a new invite!

		Permissions:
		- manage_channels
		"""

		invite = await Bans().create_invite(self.bot, interaction.guild, force_new=True)
		queue().add(ConfigUtils.log_change(interaction.guild, {"invite" : invite},
		                                   user_name=interaction.user.mention))
		await send_response(interaction, f"Your invite has been regenerated, here's your new invite: {invite}")



async def setup(bot: Bot) :
	await bot.add_cog(
		Invite(bot),
	)
