import discord
from discord import app_commands
from discord.ext.commands import GroupCog, Bot
from discord_py_utilities.messages import send_response

from classes.bans import Bans
from classes.configdata import ConfigData
from data.config.mappings import Channels
from database.transactions.ConfigTransactions import ConfigTransactions
from database.transactions.ServerTransactions import ServerTransactions


class Invite(GroupCog, name="invite", description="Manage your servers invites!") :
	"""

	"""

	def __init__(self, bot: Bot) :
		self.bot = bot

	@app_commands.command(name="set_channel", description="Sets the channel where the invite gets created.")
	async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
		ConfigTransactions().config_unique_add(interaction.guild.id, Channels.INVITE, channel.id)
		ConfigData().load_guild(interaction.guild.id)
		invite = await Bans().create_invite(self.bot, interaction.guild, force_new=True)
		ServerTransactions().update(interaction.guild.id, invite=invite)
		await send_response(interaction, f"You've changed your invite channel to {channel.mention}, here's your new invite: {invite}")

	@app_commands.command(name="regenerate", description="Generates a new invite!")
	async def regenerate(self, interaction: discord.Interaction):
		invite = await Bans().create_invite(self.bot, interaction.guild, force_new=True)
		await send_response(interaction, f"Your invite has been regenerated, here's your new invite: {invite}")



async def setup(bot: Bot) :
	await bot.add_cog(
		Invite(bot),
	)
