import asyncio
import logging
import os
import threading
from contextlib import asynccontextmanager

import discord
from discord.ext import commands
# IMPORT LOAD_DOTENV FUNCTION FROM DOTENV MODULE.
from dotenv import load_dotenv
from fastapi import FastAPI

from api import bans_router
from classes.bans import Bans
from classes.blacklist import blacklist_check
from classes.configer import Configer
from classes.queue import queue
from database.current import create_bot_database
from database.databaseController import ServerDbTransactions
from view.buttons.serverinfo import ServerInfo

# LOADS THE .ENV FILE THAT RESIDES ON THE SAME LEVEL AS THE SCRIPT.
load_dotenv('main.env')
# GRAB THE API TOKEN FROM THE .ENV FILE.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX")
DBTOKEN = os.getenv("DB")
DEV = int(os.getenv("DEV"))

create_bot_database()

# declares the bots intent
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.AutoShardedBot(command_prefix=PREFIX, case_insensitive=False, intents=intents, shard_id=1)
@asynccontextmanager
async def lifespan(app: FastAPI):
	loop = asyncio.get_event_loop()
	thread = threading.Thread(target=lambda: asyncio.run(run()))
	thread.start()
	yield
	asyncio.run_coroutine_threadsafe(bot.close(), loop).result()


app = FastAPI(lifespan=lifespan)
app.include_router(bans_router)

bot.SUPPORTGUILD = int(os.getenv('GUILD'))
bot.BANCHANNEL = int(os.getenv('BANS'))
bot.DENIALCHANNEL = int(os.getenv('DENIED'))
bot.APPROVALCHANNEL = int(os.getenv('APPROVED'))
bot.DEV = DEV


# EVENT LISTENER FOR WHEN THE BOT HAS SWITCHED FROM OFFLINE TO ONLINE.

@bot.event
async def on_ready() :
	logging.info("Bot is starting")
	devroom = bot.get_channel(DEV)
	# CREATES A COUNTER TO KEEP TRACK OF HOW MANY GUILDS / SERVERS THE BOT IS CONNECTED TO.
	guild_count = 0
	guilds = []
	# LOOPS THROUGH ALL THE GUILD / SERVERS THAT THE BOT IS ASSOCIATED WITH.
	await Configer.create_appeals()
	await Configer.create_bot_config()
	logging.info("Finished creating configs")
	queue().add(Bans().update(bot))
	logging.info("Configs and cache created")
	for guild in bot.guilds :
		# add invites
		# logging.info THE SERVER'S ID AND NAME.
		guilds.append(f"- {guild.id} (name: {guild.name}, owner: {guild.owner}({guild.owner.id}))")
		await Configer.create(guild.id, guild.name)
		if await blacklist_check(guild, devroom) :
			continue
		bot.tree.clear_commands(guild=guild)

		# INCREMENTS THE GUILD COUNTER.
		guild_count += 1

	formguilds = "\n".join(guilds)
	logging.info(f"Bot is in {guild_count} guilds:\n{formguilds}")
	queue().add(devroom.send(f"Banwatch is in {guild_count} guilds. Version 3.0: Now I remember!"), priority=2)
	bot.add_view(ServerInfo())
	logging.info(f"Commands synced, start up done! Connected to {len(guild_count)} guilds and {bot.shard_count} shards.")
	await bot.tree.sync()


@bot.event
async def on_guild_join(guild: discord.Guild) -> None :
	"""When the bot it creates a config and sends a DM to the owner with instructions."""
	# adds user to database
	log = bot.get_channel(DEV)
	membercount = len([m for m in guild.members if not m.bot])
	logging.info(
		f"Server Info: {guild}({guild.id}) has {membercount} members, it's owner is {guild.owner}({guild.owner.id}) and it was created at {guild.created_at}. This server has {len(guild.channels)} channels and {len(guild.roles)} roles.")

	if await blacklist_check(guild, log) :
		return
	# if membercount < 25 and guild.id != bot.SUPPORTGUILD:
	#     await guild.owner.send(
	#         "[SECURITY ALERT] Banwatch has left your server due to low member count. Please ensure your server has at least 25 members to use the bot. When you have reached this number, [you can reinvite the bot.](https://discord.com/oauth2/authorize?client_id=1047697525349564436)")
	#     await log.send(f"Ban watch is now in {len(bot.guilds)}! It just joined:"
	#                    f"\nGuild: {guild}({guild.id})"
	#                    f"\nOwner: {guild.owner}({guild.owner.id})"
	#                    f"\nMember count: {membercount}"
	#                    f"\n**__Leaving due to low user count__**")
	#     await guild.leave()
	#     return

	await Configer.create(guild.id, guild.name)
	logging.info("sending DM now")
	await guild.owner.send(
		"Thank you for inviting **ban watch**, please read https://wolfricoz.github.io/banwatch/ to set up the bot")
	await log.send(f"Ban watch is now in {len(bot.guilds)}! It just joined:"
	               f"\nGuild: {guild}({guild.id})"
	               f"\nOwner: {guild.owner}({guild.owner.id})"
	               f"\nMember count: {membercount}"
	               f"\n\nWelcome to the Banwatch collective!")
	# Updates ban list
	logging.info(f"{guild} joined, refreshing ban list")
	ServerDbTransactions().add(guild.id, guild.owner.name, guild.name, len(guild.members), "")
	await Bans().check_guild_invites(bot, guild)
	queue().add(Bans().update(bot), priority=0)
	approval_channel = bot.get_guild(int(os.getenv("GUILD"))).get_channel(int(os.getenv("BANS")))
	queue().add(ServerInfo().send(approval_channel, guild), priority=2)


@bot.event
async def on_guild_remove(guild) :
	log = bot.get_channel(DEV)
	await log.send(f"left {guild}({guild.id}) :(. Ban watch is now in {len(bot.guilds)}")
	logging.info(f"{guild} left, refreshing ban list")
	await Bans().update(bot)


# cogloader


@bot.event
async def setup_hook() :
	loaded = []
	for filename in os.listdir("modules") :
		if filename.endswith('.py') :
			await bot.load_extension(f"modules.{filename[:-3]}")
			loaded.append(filename[:-3])
		else :
			logging.info(f'Unable to load {filename[:-3]}')

	loaded = ", ".join(loaded)
	logging.info(f"Loaded Modules: {loaded}")


@bot.command(aliases=["cr", "reload"])
@commands.is_owner()
async def cogreload(ctx) :
	filesloaded = []
	for filename in os.listdir("modules") :
		if filename.endswith('.py') :
			await bot.reload_extension(f"modules.{filename[:-3]}")
			filesloaded.append(filename[:-3])
	fp = ', '.join(filesloaded)
	await ctx.send(f"Modules loaded: {fp}")


# EXECUTES THE BOT WITH THE SPECIFIED TOKEN.
async def run() :
	try :
		await bot.start(DISCORD_TOKEN)
	except KeyboardInterrupt :
		quit(0)
