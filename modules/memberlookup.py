import logging
import os
import time
from abc import ABC

import discord
from discord import app_commands
from discord.ext import commands

from classes.bans import Bans
from classes.support.discord_tools import send_message, send_response
from database.databaseController import BanDbTransactions


# TODO: UPDATE THIS TO WORK WITH THE DATABASE

class BanCheck(ABC):

    def member_count_check(self, guild, bot):
        if guild.id == bot.SUPPORTGUILD:
            return
        return len(guild.members) >= 50

    async def checkerall(self, interaction, bot):
        fcount = 0
        bcount = 0
        with open(f"bans.txt", 'w', encoding='utf-8') as f:
            f.write(f"Bans:")
        for member in interaction.guild.members:

            ban_list = BanDbTransactions().get_all(member.id)
            fcount += 1
            if not ban_list:
                continue
            for ban in ban_list:
                bcount += 1
                with open(f"bans.txt", 'a', encoding='utf-8') as f:
                    f.write(f"\n----{member}({member.id})----:"
                            f"\n{ban.reason}")
        with open(f"bans.txt", encoding='utf-8') as f:
            await interaction.channel.send(f"Bans found :",
                                           file=discord.File(f.name, "banned.txt"))
        os.remove(f.name)
        return fcount


class User(commands.GroupCog, name="user"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="lookup", description="Looks up user's bans and displays them in the channel")
    @app_commands.checks.has_permissions(ban_members=True)
    async def lookup(self, interaction: discord.Interaction, member: discord.User):
        logging.info(f"{interaction.user} from {interaction.guild.name} is looking up {member.name}")
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id == member.id and not interaction.guild.id == self.bot.SUPPORTGUILD:
            logging.warning(f"{interaction.user} tried to look up themselves")
            return await send_response(interaction, "You can not look up yourself!",
                                       ephemeral=True)

        sr =  BanDbTransactions().get_all(user_id=member.id)
        if sr is None:
            await send_message(interaction.channel, f"<@{member.id}> is not banned in any servers the bot is in.")
            return
        await Bans().send_to_channel(interaction, sr, member.id)

    @app_commands.command(name="lookupid", description="Looks up user's bans with user id and displays them in the channel")
    @app_commands.checks.has_permissions(ban_members=True)
    async def lookupid(self, interaction: discord.Interaction, memberid: str):
        logging.info(f"{interaction.user} from {interaction.guild.name} is looking up {memberid}")
        if interaction.user.id == memberid and not interaction.guild.id == self.bot.SUPPORTGUILD:
            logging.warning(f"{interaction.user} tried to look up themselves")
            return await send_response(interaction, "You can not look up yourself!",
                                       ephemeral=True)
        if BanCheck().member_count_check(interaction.guild, self.bot) is False:
            await send_message(interaction.channel, "This command can only be used in servers with 50 or more members, to prevent abuse.")
            return
        if Bans().is_ready() is False:
            return await send_response(interaction, "Bans not ready, please wait a moment - this usually takes 2 minutes.", ephemeral=True)
        try:
            memberid = int(memberid)
        except ValueError:
            await send_message(interaction.channel, "Please provide a valid user id")
            return
        await interaction.response.defer(ephemeral=True)

        sr = await Bans().check(self.bot, int(memberid))

        if sr is None:
            await send_message(interaction.channel, f"<@{memberid}> is not banned in any servers the bot is in.")
            return
        await Bans().send_to_channel(interaction.channel, sr, int(memberid))

    @app_commands.command(name="checkall", description="checks ALL users")
    @app_commands.checks.has_permissions(ban_members=True)
    async def checkall(self, interaction: discord.Interaction):
        if Bans().is_ready() is False:
            return await send_response(interaction, "Bans not ready, please wait a moment - this usually takes 2 minutes.", ephemeral=True)
        await send_response(interaction, f"Checking all users ({len(interaction.guild.members)}), please wait. Looking through {BanDbTransactions().count_bans()} unique bans")
        start = time.time()
        count = 0
        count += await BanCheck().checkerall(interaction, self.bot)
        end = time.time()
        total = end - start
        await send_message(interaction.channel, f"Check-up done, found {count} ban registries in {str(total)[0:4]} seconds."
                                                f"\n-# Reminder: You should reach out to the owner of the server for more information on the ban. Some of these bans may be older than the bot and have not been verified.")


async def setup(bot: commands.Bot):
    await bot.add_cog(User(bot))
