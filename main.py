# IMPORT DISCORD.PY. ALLOWS ACCESS TO DISCORD'S API.
# IMPORT THE OS MODULE.
import logging
import os
import sys
import traceback
import discord
from discord import Interaction, app_commands
from discord.app_commands import AppCommandError
from discord.ext import commands
# IMPORT LOAD_DOTENV FUNCTION FROM DOTENV MODULE.
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
import adefs
import db
from configer import Configer
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
alogger = logging.getLogger('sqlalchemy')
alogger.setLevel(logging.WARN)
handler2 = logging.FileHandler(filename='database.log', encoding='utf-8', mode='w')
handler2.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
alogger.addHandler(handler2)
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


@bot.command()
@commands.is_owner()
async def stop(ctx):
    await ctx.send("Rmrbot shutting down")
    exit()


def restart_bot():
    os.execv(sys.executable, ["python"] + sys.argv)


@bot.command()
@commands.is_owner()
async def restart(ctx):
    await ctx.send("Restarting bot...")
    restart_bot()
    await ctx.send("succesfully restarted")


@bot.command(name="sher", description="Oh god")
async def sher(ctx):
    await ctx.send(f"<:void:654990134957178901> **SCREEEEEEECHES**")

# events


# error logging for regular commands
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please fill in the required arguments")
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("You do not have permission")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("User not found")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send("Command failed: See log.")
        await ctx.send(error)
        raise error
    else:
        session.rollback()
        session.close()
        await ctx.send(error)
        raise error
# error logging for app commands (slash commands)


@bot.tree.error
async def on_app_command_error(
        interaction: Interaction,
        error: AppCommandError
):
    await interaction.followup.send(f"Command failed: {error} \nreport this to Rico")
    logger.error(traceback.format_exc())
    channel = bot.get_channel(1033787967929589831)
    await channel.send(traceback.format_exc())
    raise error

# EVENT LISTENER FOR WHEN THE BOT HAS SWITCHED FROM OFFLINE TO ONLINE.


@bot.event
async def on_ready():
    devroom = bot.get_channel(1047703677340749834)
    # CREATES A COUNTER TO KEEP TRACK OF HOW MANY GUILDS / SERVERS THE BOT IS CONNECTED TO.
    guild_count = 0
    guilds = []
    # LOOPS THROUGH ALL THE GUILD / SERVERS THAT THE BOT IS ASSOCIATED WITH.
    for guild in bot.guilds:
        # add invites
        # PRINT THE SERVER'S ID AND NAME.
        guilds.append(f"- {guild.id} (name: {guild.name})")
        await Configer.create(Configer, guild.id, guild.name)
        # INCREMENTS THE GUILD COUNTER.
        guild_count += 1
    # PRINTS HOW MANY GUILDS / SERVERS THE BOT IS IN.
    formguilds = "\n".join(guilds)
    await bot.tree.sync()
    await devroom.send(f"Banwatch is in {guild_count} guilds. Version 1.0.")

    session.close()
    return guilds

@bot.event
async def on_guild_join(guild):
    # adds user to database
    await Configer.create(Configer, guild.id, guild.name)
    print("sending DM now")
    await guild.owner.send("Thank you for inviting **ban watch**, please read https://docs.google.com/document/d/1bMtdsvr8D_8LEQha9d7BJhoqwXjLIfxRDsNWA4oORyI/edit?usp=sharing to set up the bot")
    log = bot.get_channel(1047703677340749834)
    await log.send(f"Joined {guild}({guild.id})")
    #SYNCS COMMANDS
    await bot.tree.sync()
# cogloader


@bot.event
async def setup_hook():
    for filename in os.listdir("Modules"):
        if filename.endswith('.py'):
            await bot.load_extension(f"Modules.{filename[:-3]}")
            print({filename[:-3]})
        else:
            print(f'Unable to load {filename[:-3]}')


@bot.command(aliases=["cr", "reload"])
@adefs.check_admin_roles()
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
