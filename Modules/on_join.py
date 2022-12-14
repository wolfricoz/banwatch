import logging

import discord
from discord.ext import commands
from abc import ABC, abstractmethod
import db
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, column
from datetime import datetime, timedelta
import re
import typing
from configer import Configer
import random
import os
Session = sessionmaker(bind=db.engine)
session = Session()


class Events(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        bot = self.bot
        config = await Configer.get(self, member.guild.id, "modchannel")
        configid = int(config)
        bans = bot.bans
        if f"{member.id}" in bans:
            print("member in bans")
            reasons = []
            count = 0
            for guild in bot.guilds:
                try:
                    ban = bans[f"{member.id}"][f"{guild.id}"]['reason']
                    reasons.append(f"\n {guild}: {ban}")
                    count += 1
                except discord.NotFound:
                    pass
                except Exception as e:
                    pass
            sr = "".join(reasons)

            if count >= 1:
                if configid == 0:
                    channel = member.guild.system_channel
                    await channel.send("Moderation channel is not set, use **/config change**")
                else:
                    channel = bot.get_channel(configid)
                    if len(sr) < 1800:
                        await channel.send(f"{member.mention} is banned in: {sr}")
                    else:
                        with open(f"{random.randint(1, 1000)}.txt", 'w', encoding='utf-8') as f:
                            f.write(sr)
                        await channel.send(f"{member.mention} is banned in:", file=discord.File(f.name, "banned.txt"))
                        os.remove(f.name)
        else:
            print(f"{member.guild}: {member} has no ban record")


async def setup(bot):
    await bot.add_cog(Events(bot))
