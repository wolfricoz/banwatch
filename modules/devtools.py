import os
import random
from abc import ABC

import discord
from discord.ext import commands
from sqlalchemy.orm import sessionmaker

import db
from classes.configer import Configer

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
        with open('countbans.txt', 'w'):
            pass
        testbans = []
        total = 0
        ucount = 0

        for guild in self.bot.guilds:
            try:
                invites = await guild.invites()
            except discord.Forbidden:
                invites = ['No permission']
            count = 0
            try:
                async for entry in guild.bans(limit=2000):
                    count += 1
                    if str(entry.user.id) not in testbans:
                        testbans.append(str(entry.user.id))
                        ucount += 1
                    else:
                        pass
            except discord.Forbidden:
                print(f'guild gave no permissionms: {guild.name} ({guild.owner})')
            if len(invites) < 1:
                invites = ['No invites']
            with open('countbans.txt', 'a') as f:
                f.write(f"\n{guild}'s ban count: {count}"
                        f"\nDebug: Invite: {invites[0]}, Serverid: {guild.id}, user count {guild.member_count}, Owner: {guild.owner} /n")
            total += count
        await interaction.channel.send(f"Total bans: {total}, Unique: {ucount}",
                                       file=discord.File(f.name, "countbans.txt"))

    @commands.command(name="announce", aliases=['a'])
    @commands.is_owner()
    async def announce(self, ctx, *, message: str):
        if ctx.author.id == 188647277181665280:
            for guild in self.bot.guilds:
                print(f"{guild}: owner {guild.owner} ")
                try:
                    await guild.owner.send(f"__**BAN WATCH ANNOUNCEMENT**__\n"
                                           f"{message}")
                except discord.Forbidden:
                    try:
                        config = await Configer.get(guild.id, "modchannel")
                        configid = int(config)
                        channel = self.bot.get_channel(configid)
                        await channel.send(f"__**BAN WATCH ANNOUNCEMENT**__\n"
                                           f"{message} \n (Bot could not dm owner)")
                    except:
                        print(f"couldn't dm {guild.owner}, no modchannel set")
                except Exception as e:
                    print(f"couldn't dm {guild.owner}, error reason: \n {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(dev(bot))


session.commit()
