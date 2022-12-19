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
        bcount = 0
        bans = bot.bans
        with open(f"bans.txt", 'w', encoding='utf-8') as f:
            f.write(f"Bans:")
        for member in interaction.guild.members:
            print(f"{interaction.guild}: Checking {member}")
            if f"{member.id}" in bans:
                bcount += 1
                count = 0
                print("member in bans")
                reasons = []
                for guild in bot.guilds:
                    try:
                        ban = bot.bans[f"{member.id}"][f"{guild.id}"]['reason']
                        reasons.append(f"\n{guild}: {ban}")
                        count += 1
                    except discord.NotFound:
                        pass
                    except Exception as e:
                        pass
                sr = "".join(reasons)

                if count >= 1:
                    fcount += 1
                    with open(f"bans.txt", 'a', encoding='utf-8') as f:
                        text = f.write(f"\n{member}({member.id}):"
                                f"{sr}")
                else:
                    pass
            else:
                pass
        with open(f"bans.txt", 'r', encoding='utf-8') as f:
            await interaction.channel.send(f"Bans found :",
                                           file=discord.File(f.name, "banned.txt"))
        os.remove(f.name)
        return fcount


class User(commands.GroupCog, name="user"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @app_commands.command(name="lookup", description="Looks up user's bans and displays them in the channel")
    @app_commands.checks.has_permissions(ban_members=True)
    async def lookup(self, interaction: discord.Interaction, member: discord.Member):
        start = time.time()
        await interaction.response.defer(ephemeral=True)
        count = 0
        reasons = []
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
        end = time.time()
        total = start - end
        print(total)

    @app_commands.command(name="checkall", description="checks ALL users, this command may take a while.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def checkall(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Checking all users ({len(interaction.guild.members)}), please wait. Looking through {len(self.bot.bans)} unique bans")
        start = time.time()
        count = 0
        count += await BanCheck().checkerall(interaction, self.bot)
        end = time.time()
        total = end - start
        await interaction.channel.send(f"Check-up done, found {count} ban registries in {str(total)[0:4]} seconds")

    # @app_commands.command(name="test3", description="checks ALL users, this command may take a while.")
    # @app_commands.checks.has_permissions(ban_members=True)
    # async def test(self, interaction: discord.Interaction,):
    #     await interaction.response.send_message(f"Bans found {len(self.bot.bans)}", ephemeral=True)
    #     newbans = {}
    #     bcount = 0
    #     fcount = 0
    #     for guild in self.bot.guilds:
    #         async for entry in guild.bans():
    #             if str(entry.user.id) in newbans:
    #                 newbans[f"{entry.user.id}"][f"{guild.id}"] = {}
    #                 newbans[f"{entry.user.id}"][f"{guild.id}"]['reason'] = entry.reason
    #             else:
    #                 newbans[f"{entry.user.id}"] = {}
    #                 newbans[f"{entry.user.id}"][f"{guild.id}"] = {}
    #                 newbans[f"{entry.user.id}"][f"{guild.id}"]['reason'] = entry.reason
    #     start = time.time()
    #     for member in interaction.guild.members:
    #         print(f"{interaction.guild}: Checking {member}")
    #         count = 0
    #         if f"{member.id}" in self.bot.bans:
    #             bcount += 1
    #             print(f"{member} in bans")
    #             reasons = []
    #             for guild in self.bot.guilds:
    #                 try:
    #                     ban = newbans[f"{member.id}"][f"{guild.id}"]['reason']
    #                     reasons.append(f"\n {guild}: {ban}")
    #                     count += 1
    #                 except discord.NotFound:
    #                     pass
    #                 except Exception as e:
    #                     pass
    #             sr = "".join(reasons)
    #
    #
    #
    #             if count >= 1:
    #                 fcount += 1
    #                 if bcount == 0:
    #                     with open(f"bans.txt", 'w', encoding='utf-8') as f:
    #
    #                         f.write(f"{member}({member.id}):\n"
    #                                 f"{sr}")
    #                 if bcount >= 1:
    #                     with open(f"bans.txt", 'a', encoding='utf-8') as f:
    #                         f.write(f"\n{member}({member.id}):\n"
    #                                 f"{sr}")
    #             else:
    #                 pass
    #
    #         else:
    #             pass
    #     with open(f"bans.txt", 'r', encoding='utf-8') as f:
    #         await interaction.channel.send(f"Bans found :",
    #                                        file=discord.File(f.name, "banned.txt"))
    #     os.remove(f.name)
    #     end = time.time()
    #     total = end - start
    #     await interaction.channel.send(f"finished in {str(total)[0:4]} seconds, found {fcount}")


async def setup(bot: commands.Bot):
    await bot.add_cog(User(bot))


session.commit()
