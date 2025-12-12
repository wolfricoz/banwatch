import logging

from discord.ext import commands, tasks

from classes.access import AccessControl
from classes.blacklist import blacklist_check
from classes.configdata import ConfigData
from classes.dashboard.Servers import Servers
from classes.queue import queue
from classes.tasks import pending_bans
from database.databaseController import ServerDbTransactions


class Tasks(commands.Cog) :
	def __init__(self, bot: commands.Bot) :
		self.bot = bot
		self.check_blacklist.start()
		self.check_active_servers.start()
		self.check_pending_bans.start()
		self.purge_bot_roles.start()

	def cog_unload(self) :
		self.check_blacklist.cancel()
		self.check_active_servers.cancel()
		self.check_pending_bans.cancel()
		self.purge_bot_roles.cancel()


	@tasks.loop(hours=1)
	async def check_blacklist(self) :
		if self.check_blacklist.current_loop == 0 :
			return
		print(f"[blacklist check]Checking for blacklisted servers")
		dev = self.bot.get_channel(int(self.bot.DEV))
		for guild in self.bot.guilds :
			if guild.id == self.bot.SUPPORTGUILD :
				continue
			if await blacklist_check(guild, dev) :
				continue

	@tasks.loop(hours=24)
	async def check_pending_bans(self) :
		if self.check_pending_bans.current_loop == 0 :
			return
		await pending_bans(self.bot)

	@check_pending_bans.before_loop
	async def before_check_pending_bans(self) :
		await self.bot.wait_until_ready()

	@check_blacklist.before_loop
	async def before_check_blacklist(self) :
		await self.bot.wait_until_ready()

	@tasks.loop(hours=12)
	async def check_active_servers(self) :
		logging.info(f"Checking active servers")
		guild_ids = ServerDbTransactions().get_all()
		for guild in self.bot.guilds :
			if guild.id in guild_ids :
				guild_ids.remove(guild.id)
				ServerDbTransactions().update(guild.id, active=True)
				continue
			ServerDbTransactions().add(guild.id, guild.owner.name, guild.name, len(guild.members), "")
		for gid in guild_ids :
			ServerDbTransactions().update(gid, active=False)
		guilds = ServerDbTransactions().get_all(id_only=False)
		servers = Servers()
		servers.skip = False
		for guild in guilds :
			queue().add(servers.update_server(self.bot, guild), 0)
		AccessControl().reload_premium()

	@tasks.loop(hours=1)
	async def purge_bot_roles(self) :
		# if self.purge_bot_roles.current_loop == 0 :
		# 	return
		logging.info(f"Purging bot roles from servers")
		for guild in AccessControl().premium :
			g = self.bot.get_guild(guild)
			if g is None :
				g = await self.bot.fetch_guild(guild)
			if g is None :
				logging.info(f"Could not fetch guild {guild}")
				continue
			role = g.get_role(ConfigData().get_key(guild, "trap_role", 0))
			# if not role:
			# 	role = await g.fetch_role(ConfigData().get_key(guild, "trap_role", 0))

			if role is None :
				logging.info(f"No trap role in {g.name}({g.id})")
				continue
			for member in role.members :
				try:
						queue().add(g.ban(member, reason=f"User selected the bot role and has been removed."), 0)
						logging.info(f"Removed bot {member} from trap role in {g.name}({g.id})")
				except Exception as e :
					logging.warning(f"Failed to remove bot {member} from trap role in {g.name}({g.id}): {e}", exc_info=True)



	@check_active_servers.before_loop
	async def before_check_active_servers(self) :
		await self.bot.wait_until_ready()

	@purge_bot_roles.before_loop
	async def before_purge_bot_roles(self) :
		await self.bot.wait_until_ready()


async def setup(bot) :
	await bot.add_cog(Tasks(bot))
