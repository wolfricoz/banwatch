# IMPORT DISCORD.PY. ALLOWS ACCESS TO DISCORD'S API.
# IMPORT THE OS MODULE.
import logging
import os
import sys
import traceback
import discord
from discord import Interaction, app_commands
from discord.app_commands import AppCommandError
from discord.ext import commands, tasks
# IMPORT LOAD_DOTENV FUNCTION FROM DOTENV MODULE.
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
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

bot.bans = {}
@bot.event
async def on_ready():
    devroom = bot.get_channel(1047703677340749834)
    # Fills banlist
    bot.bans
    for guild in bot.guilds:
        async for entry in guild.bans():
            if str(entry.user.id) in bot.bans:
                bot.bans[f"{entry.user.id}"][f"{guild.id}"] = {}
                bot.bans[f"{entry.user.id}"][f"{guild.id}"]['reason'] = entry.reason
            else:
                bot.bans[f"{entry.user.id}"] = {}
                bot.bans[f"{entry.user.id}"][f"{guild.id}"] = {}
                bot.bans[f"{entry.user.id}"][f"{guild.id}"]['reason'] = entry.reason
    import json
    with open('test.json', 'w') as f:
        json.dump(bot.bans, f, indent=4)
        print("done!")

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
    await devroom.send(f"Banwatch is in {guild_count} guilds. Version 1.2")
    session.close()
    return guilds

@bot.event
async def on_member_ban(guild, user):
    """Updates banlist when user is banned"""
    print(f"{guild}: banned {user}, refreshing banlist")
    newbans = {}
    for guild in bot.guilds:
        async for entry in guild.bans():
            if str(entry.user.id) in newbans:
                newbans[f"{entry.user.id}"][f"{guild.id}"] = {}
                newbans[f"{entry.user.id}"][f"{guild.id}"]['reason'] = entry.reason
            else:
                newbans[f"{entry.user.id}"] = {}
                newbans[f"{entry.user.id}"][f"{guild.id}"] = {}
                newbans[f"{entry.user.id}"][f"{guild.id}"]['reason'] = entry.reason
    bot.bans = newbans
    print("List updated")

@bot.listen()
async def on_member_ban(guild, user):
    """informs other servers an user is banned"""
    ban = await guild.fetch_ban(user)
    for guilds in bot.guilds:
        if user in guilds.members:
            config = await Configer.get(None, guilds.id, "modchannel")
            modchannel = bot.get_channel(int(config))
            await modchannel.send(f"{user} ({user.id}) was banned in {guild} for {ban.reason}")




@bot.event
async def on_member_unban(guild, user):
    """Updates banlist when user is unbanned"""
    print(f"{guild}: unbanned {user}, refreshing banlist")
    newbans = {}
    for guild in bot.guilds:
        async for entry in guild.bans():
            if str(entry.user.id) in newbans:
                newbans[f"{entry.user.id}"][f"{guild.id}"] = {}
                newbans[f"{entry.user.id}"][f"{guild.id}"]['reason'] = entry.reason
            else:
                newbans[f"{entry.user.id}"] = {}
                newbans[f"{entry.user.id}"][f"{guild.id}"] = {}
                newbans[f"{entry.user.id}"][f"{guild.id}"]['reason'] = entry.reason
    bot.bans = newbans
    print("List updated")


@bot.event
async def on_guild_join(guild):
    # adds user to database
    await Configer.create(Configer, guild.id, guild.name)
    print("sending DM now")
    await guild.owner.send("Thank you for inviting **ban watch**, please read https://docs.google.com/document/d/1bMtdsvr8D_8LEQha9d7BJhoqwXjLIfxRDsNWA4oORyI/edit?usp=sharing to set up the bot")
    log = bot.get_channel(1047703677340749834)
    await log.send(f"Joined {guild}({guild.id}). Ban watch is now in {len(bot.guilds)}")
    #SYNCS COMMANDS
    await bot.tree.sync()
    # Updates ban list
    print(f"{guild} joined, refreshing ban list")
    newbans = {}
    for guild in bot.guilds:
        async for entry in guild.bans():
            if str(entry.user.id) in newbans:
                newbans[f"{entry.user.id}"][f"{guild.id}"] = {}
                newbans[f"{entry.user.id}"][f"{guild.id}"]['reason'] = entry.reason
            else:
                newbans[f"{entry.user.id}"] = {}
                newbans[f"{entry.user.id}"][f"{guild.id}"] = {}
                newbans[f"{entry.user.id}"][f"{guild.id}"]['reason'] = entry.reason
    bot.bans = newbans
    print("List updated")

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
