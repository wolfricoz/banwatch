"""Logs all the happenings of the bot."""
import logging
import os
import time
import traceback
from sys import platform

import discord.utils
from discord import Interaction, app_commands
from discord.app_commands import AppCommandError, command, CheckFailure
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv('main.env')
channels72 = os.getenv('channels72')
spec = os.getenv('spec')
channels24 = os.getenv('channels24')
single = os.getenv('single')
test = os.getenv('test')
count = 0
os.environ['TZ'] = 'America/New_York'
if platform == "linux" or platform == "linux2":
    time.tzset()
logfile = f"logs/log-{time.strftime('%m-%d-%Y')}.txt"

if os.path.exists('logs') is False:
    print("Making logd directory")
    os.mkdir('logs')

if os.path.exists(logfile) is False:
    with open(logfile, 'w') as f:
        f.write("logging started")

with open(logfile, 'a') as f:
    f.write(f"\n\n----------------------------------------------------"
            f"\nbot started at: {time.strftime('%c %Z')}\n"
            f"----------------------------------------------------\n\n")

logger = logging.getLogger('discord')
logger.setLevel(logging.WARN)
handler = logging.FileHandler(filename=logfile, encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
alogger = logging.getLogger('sqlalchemy')
alogger.setLevel(logging.WARN)
handler2 = logging.FileHandler(filename=logfile, encoding='utf-8', mode='a')
handler2.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logging.basicConfig(filename=logfile, encoding='utf-8', level=logging.DEBUG, filemode='a')

alogger.addHandler(handler2)


class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_command_error")
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """handles chat-based command errors."""
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
            logger.warning(f"\n{ctx.guild.name} {ctx.guild.id} {ctx.command.name}: {error}")
            channel = self.bot.get_channel(self.bot.DEV)
            with open('error.txt', 'w', encoding='utf-16') as file:
                file.write(str(error))
            await channel.send(
                    f"{ctx.guild.name} {ctx.guild.id}: {ctx.author}: {ctx.command.name}",
                    file=discord.File(file.name, "error.txt"))
            print('error logged')
            print(traceback.format_exc())

    def cog_load(self):
        tree = self.bot.tree
        self._old_tree_error = tree.on_error
        tree.on_error = self.on_app_command_error

    def cog_unload(self):
        tree = self.bot.tree
        tree.on_error = self._old_tree_error

    async def on_fail_message(self, interaction: Interaction, message: str):
        """sends a message to the user if the command fails."""
        try:
            await interaction.channel.send(message)
        except Exception as e:
            logging.error(e)

    async def on_app_command_error(
            self,
            interaction: Interaction,
            error: AppCommandError
    ):
        """app command error handler."""
        try:
            data = [f"{a['name']}: {a['value']}" for a in interaction.data['options']]
            formatted_data = ", ".join(data)
        except KeyError:
            formatted_data = "KeyError/No data"
        channel = self.bot.get_channel(self.bot.DEV)
        if isinstance(error, CheckFailure):
            await self.on_fail_message(interaction, "You do not have permission.")
            return
        elif isinstance(error, commands.MemberNotFound):
            await self.on_fail_message(interaction, "User not found.")
            return

        with open('error.txt', 'w', encoding='utf-8') as file:
            file.write(traceback.format_exc())
        try:
            await channel.send(
                    f"{interaction.guild.name} {interaction.guild.id}: {interaction.user}: {interaction.command.name} with arguments {formatted_data}",
                    file=discord.File(file.name, "error.txt"))
        except Exception as e:
            logging.error(e)
        logger.warning(
                f"\n{interaction.guild.name} {interaction.guild.id} {interaction.command.name} with arguments {formatted_data}: {traceback.format_exc()}")

        await self.on_fail_message(interaction, f"Command failed: {error} \nreport this to Rico")
        # raise error

    @commands.Cog.listener(name='on_command')
    async def print(self, ctx: commands.Context):
        """logs the chat command when initiated"""
        server = ctx.guild
        user = ctx.author
        commandname = ctx.command
        logging.debug(f'\n{server.name}({server.id}): {user}({user.id}) issued command: {commandname}')

    @commands.Cog.listener(name='on_app_command_completion')
    async def appprint(self, interaction: Interaction, commandname: command):
        """logs the app command when finished."""
        server = interaction.guild
        user = interaction.user
        try:
            logging.debug(f'\n{server.name}({server.id}): {user}({user.id}) issued appcommand: `{commandname.name}` with arguments: {interaction.data["options"]}')
        except KeyError:
            logging.debug(f'\n{server.name}({server.id}): {user}({user.id}) issued appcommand: `{commandname.name}` with no arguments.')

    @app_commands.command(name="getlog")
    async def getlog(self, interaction: Interaction):
        """gets the log file"""
        with open(logfile, 'rb') as file:
            await interaction.response.send_message("Here's the log file.", file=discord.File(file.name, "log.txt"))


async def setup(bot):
    """Adds the cog to the bot."""
    await bot.add_cog(Logging(bot))
