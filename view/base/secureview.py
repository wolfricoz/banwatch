import discord
from discord_py_utilities.messages import send_response

from classes.configer import Configer
from data.variables.messages import BotMessages


class SecureView(discord.ui.View) :
	async def interaction_check(self, interaction: discord.Interaction) -> bool :
		if await Configer.is_user_blacklisted(interaction.user.id) :
			await send_response(interaction, str(BotMessages.BLACKISTED))
			return False
		return True
