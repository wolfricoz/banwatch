import os
import traceback
import logging
import discord.utils
from discord.ext import commands
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
import db
from discord import Interaction
from discord.app_commands import AppCommandError, command

Session = sessionmaker(bind=db.engine)
session = Session()
load_dotenv('main.env')
channels72 = os.getenv('channels72')
spec = os.getenv('spec')
channels24 = os.getenv('channels24')
single = os.getenv('single')
test = os.getenv('test')
count = 0
if os.path.exists('logs'):
    d = os.listdir('logs')
    count = len(d)
    print(count)
else:
    os.mkdir('logs')
    count = 0
with open(f'logs/log{count}', 'w') as f:
    f.write("logging started")
    print(f.name)

logger = logging.getLogger('discord')
logger.setLevel(logging.WARN)
handler = logging.FileHandler(filename=f.name, encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
alogger = logging.getLogger('sqlalchemy')
alogger.setLevel(logging.WARN)
handler2 = logging.FileHandler(filename=f.name, encoding='utf-8', mode='a')
handler2.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logging.basicConfig(filename=f.name, encoding='utf-8', level=logging.DEBUG, filemode='a')

alogger.addHandler(handler2)
class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_command_error")
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please fill in the required arguments")
        elif isinstance(error, commands.CommandNotFound):
            pass
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("You do not have permission")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("User not found")
        # elif isinstance(error, commands.CommandInvokeError):
        #     await ctx.send("Command failed: See log.")
        #     await ctx.send(error)
        #     logging.warning(error)
        #     raise error
        else:
            await ctx.send(error)
            logger.warning(f"\n{ctx.guild.name} {ctx.guild.id} {ctx.command.name}: {error}")
            channel = self.bot.get_channel(1033787967929589831)
            with open('error.txt', 'w', encoding='utf-8') as f:
                f.write(str(error))
            await channel.send(
                f"{ctx.guild.name} {ctx.guild.id}: {ctx.author}: {ctx.command.name}",
                file=discord.File(f.name, "error.txt"))
            print('error logged')

    def cog_load(self):
        tree = self.bot.tree
        self._old_tree_error = tree.on_error
        tree.on_error = self.on_app_command_error

    def cog_unload(self):
        tree = self.bot.tree
        tree.on_error = self._old_tree_error

    async def on_app_command_error(
        self,
        interaction: Interaction,
        error: AppCommandError
    ):
        if isinstance(error, commands.BotMissingPermissions) or isinstance(error, commands.BotMissingAnyRole):
            await interaction.followup.send("The bot does not have the required permissions. Please ensure it has the ban permission to read the banlist and the permissions to see and send messages in the channel.")
            return
        await interaction.followup.send(f"Command failed: {error} \nreport this to Rico")
        channel = self.bot.get_channel(1033787967929589831)
        with open('error.txt', 'w', encoding='utf-8') as f:
            f.write(traceback.format_exc())
        await channel.send(f"{interaction.guild.name} {interaction.guild.id}: {interaction.user}: {interaction.command.name}", file=discord.File(f.name, "error.txt"))
        logger.warning(f"\n{interaction.guild.name} {interaction.guild.id} {interaction.command.name}: {traceback.format_exc()}")
        # raise error

    @commands.Cog.listener(name='on_command')
    async def print(self, ctx):
        server = ctx.guild
        user = ctx.author
        command = ctx.command
        logging.debug(f'\n{server.name}({server.id}): {user}({user.id}) issued command: {command}')

    @commands.Cog.listener(name='on_app_command_completion')
    async def print(self, ctx: Interaction, command: command):
        server = ctx.guild
        user = ctx.user
        logging.debug(f'\n{server.name}({server.id}): {user}({user.id}) issued appcommand: {command.name}')

async def setup(bot):
    await bot.add_cog(Logging(bot))
