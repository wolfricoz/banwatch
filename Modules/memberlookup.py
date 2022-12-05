import discord
from discord import app_commands
from discord.ext import commands
from abc import ABC, abstractmethod

import configer
import db
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, column
import typing
from discord import app_commands
import os
import logging
from configer import Configer
Session = sessionmaker(bind=db.engine)
session = Session()
import random
from discord.app_commands import Choice
class user(commands.GroupCog, name="user"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @app_commands.command(name="lookup", description="**CONFIG COMMAND**: Sets up the channels for the bot.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def lookup(self, interaction: discord.Interaction, member: discord.Member):

        await interaction.response.defer(ephemeral=True)
        count = 0
        reasons = []
        config = await Configer.get(Configer, interaction.guild.id, "modchannel")
        for guild in self.bot.guilds:
            try:
                ban = await guild.fetch_ban(member)
                reasons.append(f"\n {guild}: {ban.reason}")
                count += 1
            except discord.NotFound:
                print(f'{guild}: not found')
            except Exception as e:
                print(e)
        sr = "".join(reasons)

        if count >= 1:
            if len(sr) < 1800:
                await interaction.channel.send(f"{member.mention} is banned in: {sr}")
            else:
                with open(f"{random.randint(1, 1000)}.txt", 'w', encoding='utf-8') as f:
                    print(sr)
                    f.write(sr)
                await interaction.channel.send(f"{member.mention} is banned in:",
                                               file=discord.File(f.name, "banned.txt"))
                os.remove(f.name)
        else:
            await interaction.channel.send(f"{member.mention} is not banned in any servers the bot is in.")
        await interaction.followup.send(f"{member.mention} has been looked up")


async def setup(bot: commands.Bot):
    await bot.add_cog(user(bot))

session.commit()