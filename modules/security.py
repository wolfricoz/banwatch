import discord
from discord.ext import commands
from discord_py_utilities.messages import send_response

from classes.configer import Configer


class Security(commands.Cog) :
	def __init__(self, bot: commands.Bot) :
		self.bot = bot
		bot.tree.interaction_check = self.interaction_check

	async def interaction_check(self, interaction: discord.Interaction) :
		"""This function is a global check performed by every / command, to apply security checks to all commands."""
		if await Configer.is_user_blacklisted(interaction.user.id) :
			await send_response(interaction,
			                    "You are blacklisted from using this bot.",
			                    ephemeral=True
			                    )
			return False
		return True


async def setup(bot) :
	await bot.add_cog(Security(bot))
