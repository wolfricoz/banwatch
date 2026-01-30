import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord_py_utilities.messages import send_response

from classes.access import AccessControl
from classes.queue import queue


class QueueTask(commands.Cog) :
	status = None

	def __init__(self, bot: commands.Bot) :
		self.bot = bot
		self.queue.start()
		self.display_status.start()

	def cog_unload(self) :
		self.queue.cancel()

	@app_commands.command(name="restart_queue", description="[dev command] Restart the bot queue")
	@AccessControl().check_access('dev')
	async def restart_queue(self, interaction: discord.Interaction, empty=False) :
		if empty :
			queue().clear()
		queue().task_finished = True
		self.queue.restart()
		await send_response(interaction, f"Queue restarted. Empty: {empty}", ephemeral=True)


	@tasks.loop(seconds=0.4)
	async def queue(self) :
		await queue().start()

	@tasks.loop(seconds=3)
	async def display_status(self) :
		await self.bot.wait_until_ready()
		status = "over the community"
		if not queue().empty() :
			status = f"Processing {len(queue().status())} bans"
			status = queue().status()
		if self.status and self.status == status :
			return
		self.status = status
		await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status))

	@queue.before_loop
	async def before_queue(self) :
		await self.bot.wait_until_ready()

	@queue.before_loop
	async def before_display(self) :
		await self.bot.wait_until_ready()


async def setup(bot) :
	await bot.add_cog(QueueTask(bot))
