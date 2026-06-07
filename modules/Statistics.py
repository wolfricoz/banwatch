import discord
from discord import app_commands
from discord.ext.commands import Bot, GroupCog
from discord_py_utilities.messages import send_message

from classes.support.Graphs import clean_pie, create_pie
from database.transactions.BanTransactions import BanTransactions
import numpy as np

class Statistics(GroupCog, name="statistics") :
	"""
		View your servers statistics!
	"""

	def __init__(self, bot: Bot) :
		self.bot = bot

	pass

	@app_commands.command(name="bans", description="Shows the stats of your bans!")
	async def bans(self, interaction: discord.Interaction) :
		db_data = BanTransactions().status_statistic(interaction.guild_id)

		# Prepare the data
		tags = list(db_data.keys())
		data = list(db_data.values())

		# Create the chart with the data.
		# TODO: Make it actually show the amount, not percentages.
		file = create_pie(interaction.guild_id, data, tags)
		await send_message(interaction.channel, f"-# Note: Bans may be hidden due to insufficient evidence, unclear justification, low value to external servers, privacy protection, or if the ban is outdated. You can view them on the dashboard!", files=[discord.File(fp=file, filename="ban_status.png")])
		clean_pie(interaction.guild_id)







async def setup(bot: Bot) :
	await bot.add_cog(
		Statistics(bot),
	)
