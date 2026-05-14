from discord.ext.commands import GroupCog, Bot


class Warnings(GroupCog) :

	def __init__(self, bot: Bot) :
		self.bot = bot

	# Add warning

	# view/manage warnings UI (Edit, Delete, Add Evidence)



	pass


async def setup(bot: Bot) :
	await bot.add_cog(
		Warnings(bot),
	)
