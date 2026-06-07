import discord
from discord import app_commands
from discord.ext.commands import Bot, GroupCog
from discord_py_utilities.messages import send_message

from classes.support.Graphs import clean_pie, clean_trend, create_ban_trend_chart, create_pie
from database.transactions.BanTransactions import BanTransactions


class Statistics(GroupCog, name="statistics") :
	"""
		View your servers statistics!
	"""

	def __init__(self, bot: Bot) :
		self.bot = bot

	pass

	@app_commands.command(name="bans", description="Shows the stats of your bans!")
	@app_commands.guild_only()
	@app_commands.checks.has_permissions(manage_messages=True)
	async def bans(self, interaction: discord.Interaction) :
		db_data = BanTransactions().status_statistic(interaction.guild_id)

		# Prepare the data
		tags = list(db_data.keys())
		data = list(db_data.values())

		# Create the chart with the data.
		# TODO: Make it actually show the amount, not percentages.
		file = create_pie(interaction.guild_id, data, tags, "# of bans by status")
		await send_message(interaction.channel, f"-# Note: Bans may be hidden due to insufficient evidence, unclear justification, low value to external servers, privacy protection, or if the ban is outdated. You can view them on the dashboard!", files=[discord.File(fp=file, filename="ban_status.png")])
		clean_pie(interaction.guild_id)

	@app_commands.command(name="trend", description="Show the trend in your bans!")
	@app_commands.guild_only()
	@app_commands.checks.has_permissions(manage_messages=True)
	async def trend(self, interaction: discord.Interaction, days: int = 30) :
		db_data = BanTransactions().trend_statistic(interaction.guild_id, days)

		file = create_ban_trend_chart(interaction.guild_id, db_data)
		await send_message(interaction.channel, f" ", files=[discord.File(fp=file, filename="ban_status.png")])
		clean_trend(interaction.guild_id)






async def setup(bot: Bot) :
	await bot.add_cog(
		Statistics(bot),
	)
