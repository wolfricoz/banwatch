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



class BanCheck(ABC):

    def member_count_check(self, guild, bot):
        if guild.id == bot.SUPPORTGUILD:
            return
        return len(guild.members) >= 50

    async def checkerall(self, interaction, bot):
        fcount = 0
        bcount = 0
        start = time.time()
        ban_list = BanDbTransactions().get_all()
        end = time.time()
        total = end - start
        print(f"Getting bans: {total}")
        with open(f"bans.txt", 'w', encoding='utf-8') as f:
            f.write(f"Bans:")
        start = time.time()
        for member in interaction.guild.members:

            # Once done with the rest, get this back to 0.30 seconds if possible.
            # A good way would potentially be turning it into a dict.
            members_bans = [row for row in ban_list if row.uid == member.id]

            fcount += 1
            if not ban_list:
                continue
            for ban in members_bans:
                bcount += 1
                with open(f"bans.txt", 'a', encoding='utf-8') as f:
                    f.write(f"\n----{member}({member.id})----:"
                            f"\n{ban.reason}")
        end = time.time()
        total = end - start
        print(f"Fetching bans and appending: {total}")
        with open(f"bans.txt", encoding='utf-8') as f:
            await interaction.channel.send(f"Bans found :",
                                           file=discord.File(f.name, "banned.txt"))
        os.remove(f.name)
        return bcount


class User(commands.GroupCog, name="user"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="lookup", description="Looks up user's bans and displays them in the channel")
    @app_commands.checks.has_permissions(ban_members=True)
    async def lookup(self, interaction: discord.Interaction, member: discord.User):
        logging.info(f"{interaction.user} from {interaction.guild.name} is looking up {member.name}")
        if interaction.user.id == member.id and not interaction.guild.id == self.bot.SUPPORTGUILD:
            logging.warning(f"{interaction.user} tried to look up themselves")
            return await send_response(interaction, "You can not look up yourself!",
                                       ephemeral=True)
        sr =  BanDbTransactions().get_all_user(user_id=member.id)
        if sr is None:
            await send_response(interaction, f"<@{member.id}> is not banned in any servers the bot is in.")
            return
        await send_response(interaction, "⌛ Fetching bans, please wait.", ephemeral=True)
        await Bans().send_to_interaction_channel(interaction, sr, member)

    @app_commands.command(name="checkall", description="checks ALL users")
    @app_commands.checks.has_permissions(ban_members=True)
    async def checkall(self, interaction: discord.Interaction):
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
