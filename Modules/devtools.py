import os
from abc import ABC, abstractmethod
import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.orm import sessionmaker
import db
from configer import Configer
import random
import time
import asyncio
Session = sessionmaker(bind=db.engine)
session = Session()


class BanCheck(ABC):

    async def checkerall(self, interaction, bot):
        fcount = 0
        bans = bot.bans
        for member in interaction.guild.members:
            print(f"{interaction.guild}: Checking {member}")
            if f"{member.id}" in bans:
                count = 0
                print("member in bans")
                reasons = []
                for guild in bot.guilds:
                    try:
                        ban = bot.bans[f"{member.id}"][f"{guild.id}"]['reason']
                        reasons.append(f"\n {guild}: {ban}")
                        count += 1
                    except discord.NotFound:
                        pass
                    except Exception as e:
                        pass
                sr = "".join(reasons)


                if count >= 1:
                    fcount += 1
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
                    pass
            else:
                pass
        return fcount


class dev(commands.Cog, name="dev"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="countbans", aliases=['cb'])
    @commands.is_owner()
    async def cb(self, interaction: discord.Interaction):
        testbans = []
        total = 0
        ucount = 0
        for guild in self.bot.guilds:
            count = 0
            async for entry in guild.bans(limit=2000):
                count += 1
                if str(entry.user.id) not in testbans:
                    testbans.append(str(entry.user.id))
                    ucount += 1
                else:
                    print("ban already known")
            await interaction.channel.send(f"{guild}'s ban count: {count}")
            total += count
        await interaction.channel.send(f"Total bans: {total}, Unique: {ucount}")

    @commands.command(name="bugtest", aliases=['bug'])
    @commands.is_owner()
    async def bug(self, interaction: discord.Interaction):
        import json
        newbans = {}
        total = 0
        ucount = 0
        print(self.bot.bans["474365489670389771"])
        for guild in self.bot.guilds:
            async for entry in guild.bans():
                if str(entry.user.id) in newbans:
                    newbans[f"{entry.user.id}"][f"{guild.id}"] = {}
                    newbans[f"{entry.user.id}"][f"{guild.id}"]['reason'] = entry.reason
                else:
                    newbans[f"{entry.user.id}"] = {}
                    newbans[f"{entry.user.id}"][f"{guild.id}"] = {}
                    newbans[f"{entry.user.id}"][f"{guild.id}"]['reason'] = entry.reason
        with open('test.json', 'w') as f:
            json.dump(newbans, f, indent=4)
            print("done!")


    # @app_commands.command(name="checkall", description="checks ALL users, this command may take a while.")
    # @app_commands.checks.has_permissions(ban_members=True)
    # async def checkall(self, interaction: discord.Interaction):
    #     await interaction.response.send_message(f"Checking all users, please wait.")
    #     start = time.time()
    #     count = 0
    #     count += await BanCheck().checkerall(interaction, self.bot)
    #     end = time.time()
    #     total = end - start
    #     await interaction.channel.send(f"Check-up done, found {count} ban registries in {round(total)} seconds")



async def setup(bot: commands.Bot):
    await bot.add_cog(dev(bot))


session.commit()
