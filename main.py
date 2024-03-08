# IMPORT DISCORD.PY. ALLOWS ACCESS TO DISCORD'S API.
# IMPORT THE OS MODULE.
import logging
import os

import discord
from discord.ext import commands
# IMPORT LOAD_DOTENV FUNCTION FROM DOTENV MODULE.
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker

import db
from classes.bans import Bans
from classes.configer import Configer

# LOADS THE .ENV FILE THAT RESIDES ON THE SAME LEVEL AS THE SCRIPT.
load_dotenv('main.env')
# GRAB THE API TOKEN FROM THE .ENV FILE.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX")
DBTOKEN = os.getenv("DB")
# declares the bots intent
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, case_insensitive=False, intents=intents)

exec(open("db.py").read())
db.engine.echo = False
# database sessionmaker
Session = sessionmaker(bind=db.engine)
session = Session()


# EVENT LISTENER FOR WHEN THE BOT HAS SWITCHED FROM OFFLINE TO ONLINE.

@bot.event
async def on_ready():
    devroom = bot.get_channel(1047703677340749834)
    # Fills banlist
    await Bans().update(bot)

    # CREATES A COUNTER TO KEEP TRACK OF HOW MANY GUILDS / SERVERS THE BOT IS CONNECTED TO.
    guild_count = 0
    guilds = []
    # LOOPS THROUGH ALL THE GUILD / SERVERS THAT THE BOT IS ASSOCIATED WITH.
    for guild in bot.guilds:
        # add invites
        # logging.info THE SERVER'S ID AND NAME.
        guilds.append(f"- {guild.id} (name: {guild.name})")
        await Configer.create(guild.id, guild.name)
        # INCREMENTS THE GUILD COUNTER.
        guild_count += 1
    # logging.infoS HOW MANY GUILDS / SERVERS THE BOT IS IN.
    formguilds = "\n".join(guilds)

    await bot.tree.sync()
    # await devroom.send(f"Banwatch is in {guild_count} guilds. Version 1.4")
    session.close()
    return guilds


@bot.event
async def on_member_ban(guild, user):
    """Updates banlist when user is banned"""
    logging.info(f"{guild}: banned {user}, refreshing banlist")
    try:
        await Bans().update(bot)
    except discord.Forbidden:
        try:
            await guild.owner.send("[Permission ERROR] I need the ban permission to view the server's ban list. Please give me the ban permission.")
        except discord.Forbidden:
            logging.error(f"Unable to send message to {guild.owner} after trying to inform about missing permissions")
    logging.info("List updated")


@bot.listen()
async def on_member_ban(guild, user):
    """informs other servers an user is banned"""
    ban = await guild.fetch_ban(user)
    for guilds in bot.guilds:
        if user in guilds.members:
            config = await Configer.get(guilds.id, "modchannel")
            modchannel = bot.get_channel(int(config))
            try:
                await modchannel.send(f"{user} ({user.id}) was banned in {guild}({guild.owner}) for {ban.reason}.")
            except AttributeError:
                await guild.text_channels[0].send("You have not set a moderation channel")


@bot.event
async def on_member_unban(guild, user):
    """Updates banlist when user is unbanned"""
    logging.info(f"{guild}: unbanned {user}, refreshing banlist")
    await Bans().update(bot)
    logging.info("List updated")


@bot.event
async def on_guild_join(guild):
    """When the bot it creates a config and sends a DM to the owner with instructions."""
    # adds user to database
    await Configer.create(guild.id, guild.name)
    logging.info("sending DM now")
    await guild.owner.send("Thank you for inviting **ban watch**, please read https://docs.google.com/document/d/1bMtdsvr8D_8LEQha9d7BJhoqwXjLIfxRDsNWA4oORyI/edit?usp=sharing to set up the bot")
    log = bot.get_channel(1047703677340749834)
    await log.send(f"Joined {guild}({guild.id}). Ban watch is now in {len(bot.guilds)}")
    # SYNCS COMMANDS
    await bot.tree.sync()
    # Updates ban list
    logging.info(f"{guild} joined, refreshing ban list")
    await Bans().update(bot)


@bot.event
async def on_guild_remove(guild):
    log = bot.get_channel(1047703677340749834)
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
    session.rollback()
    session.close()
    await bot.tree.sync()


# EXECUTES THE BOT WITH THE SPECIFIED TOKEN.
bot.run(DISCORD_TOKEN)
