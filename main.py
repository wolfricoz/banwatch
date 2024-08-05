import logging
import os

import discord
from discord.ext import commands
# IMPORT LOAD_DOTENV FUNCTION FROM DOTENV MODULE.
from dotenv import load_dotenv

from classes.bans import Bans
from classes.cacher import LongTermCache
from classes.configer import Configer

# LOADS THE .ENV FILE THAT RESIDES ON THE SAME LEVEL AS THE SCRIPT.
load_dotenv('main.env')
# GRAB THE API TOKEN FROM THE .ENV FILE.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX")
DBTOKEN = os.getenv("DB")
DEV = int(os.getenv("DEV"))

# declares the bots intent
intents = discord.Intents.default()
# intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, case_insensitive=False, intents=intents)
bot.SUPPORTGUILD = int(os.getenv('GUILD'))
bot.BANCHANNEL = int(os.getenv('BANS'))
bot.DENIALCHANNEL = int(os.getenv('DENIED'))
bot.APPROVALCHANNEL = int(os.getenv('APPROVED'))
bot.DEV = DEV

# EVENT LISTENER FOR WHEN THE BOT HAS SWITCHED FROM OFFLINE TO ONLINE.

@bot.event
async def on_ready():
    devroom = bot.get_channel(DEV)
    # CREATES A COUNTER TO KEEP TRACK OF HOW MANY GUILDS / SERVERS THE BOT IS CONNECTED TO.
    guild_count = 0
    guilds = []
    # LOOPS THROUGH ALL THE GUILD / SERVERS THAT THE BOT IS ASSOCIATED WITH.
    for guild in bot.guilds:
        # add invites
        # logging.info THE SERVER'S ID AND NAME.
        guilds.append(f"- {guild.id} (name: {guild.name})")
        await Configer.create(guild.id, guild.name)
        await Configer.create_bot_config()
        await Configer.create_appeals()
        LongTermCache().create()
        if await Configer.is_blacklisted(guild.id):
            logging.info(f"Leaving {guild.name} because it is blacklisted")
            await guild.leave()
            continue
        # INCREMENTS THE GUILD COUNTER.
        guild_count += 1
    # logging.infoS HOW MANY GUILDS / SERVERS THE BOT IS IN.
    # formguilds = "\n".join(guilds)

    await bot.tree.sync()
    await devroom.send(f"Banwatch is in {guild_count} guilds. Version 2.1.1")
    return guilds


@bot.event
async def on_guild_join(guild):
    """When the bot it creates a config and sends a DM to the owner with instructions."""
    # adds user to database
    if await Configer.is_blacklisted(guild.id):
        logging.info(f"Leaving {guild.name} because it is blacklisted")
        await guild.leave()
        return
    await Configer.create(guild.id, guild.name)
    logging.info("sending DM now")
    await guild.owner.send("Thank you for inviting **ban watch**, please read https://wolfricoz.github.io/banwatch/ to set up the bot")
    log = bot.get_channel(DEV)
    await log.send(f"Joined {guild}({guild.id}). Ban watch is now in {len(bot.guilds)}")
    # SYNCS COMMANDS
    await bot.tree.sync()
    # Updates ban list
    logging.info(f"{guild} joined, refreshing ban list")
    await Bans().update(bot)


@bot.event
async def on_guild_remove(guild):
    log = bot.get_channel(DEV)
    await log.send(f"left {guild}({guild.id}) :(. Ban watch is now in {len(bot.guilds)}")
    logging.info(f"{guild} left, refreshing ban list")
    await Bans().update(bot)


# cogloader


@bot.event
async def setup_hook():
    for filename in os.listdir("modules"):
        if filename.endswith('.py'):
            await bot.load_extension(f"modules.{filename[:-3]}")
            logging.info({filename[:-3]})
        else:
            logging.info(f'Unable to load {filename[:-3]}')


@bot.command(aliases=["cr", "reload"])
@commands.is_owner()
async def cogreload(ctx):
    filesloaded = []
    for filename in os.listdir("modules"):
        if filename.endswith('.py'):
            await bot.reload_extension(f"modules.{filename[:-3]}")
            filesloaded.append(filename[:-3])
    fp = ', '.join(filesloaded)
    await ctx.send(f"Modules loaded: {fp}")
    await bot.tree.sync()


# EXECUTES THE BOT WITH THE SPECIFIED TOKEN.
bot.run(DISCORD_TOKEN)
