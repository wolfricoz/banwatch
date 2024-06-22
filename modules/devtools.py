import logging
import os
import random
from abc import ABC

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

from classes.bans import Bans
from classes.configer import Configer
from classes.queue import queue


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


OWNER = int(os.getenv("OWNER"))
GUILD = int(os.getenv("GUILD"))


def in_guild():
    async def predicate(interaction: discord.Interaction):
        if interaction.guild is None:
            return False
        if interaction.guild.id != GUILD:
            return False
        if interaction.user.id != OWNER:
            return False
        return True

    return app_commands.check(predicate)


class dev(commands.GroupCog, name="dev"):

    def __init__(self, bot):
        self.bot = bot

    async def inform_server(self, guilds, banembed):
        config = await Configer.get(guilds.id, "modchannel")
        modchannel = self.bot.get_channel(int(config))
        await modchannel.send(embed=banembed)

    @app_commands.command(name="countbans", description="[DEV] Counts all bans in all servers", )
    @in_guild()
    async def countbans(self, interaction: discord.Interaction):
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

    @app_commands.command(name="announce", description="[DEV] Send an announcement to all guild owners")
    @in_guild()
    async def announce(self, interaction: discord.Interaction, message: str):
        if interaction.user.id != 188647277181665280:
            return

        dmed = []
        for guild in self.bot.guilds:
            print(f"{guild}: owner {guild.owner} ")

            if guild.owner.id in dmed:
                continue

            dmed.append(guild.owner.id)
            try:
                await guild.owner.send(f"__**BAN WATCH ANNOUNCEMENT**__\n{message}")
            except discord.Forbidden:
                try:
                    config = await Configer.get(guild.id, "modchannel")
                    configid = int(config)
                    channel = self.bot.get_channel(configid)
                    await channel.send(f"__**BAN WATCH ANNOUNCEMENT**__\n{message} \n (Bot could not dm owner)")
                except:
                    print(f"couldn't dm {guild.owner}, no modchannel set")
            except Exception as e:
                print(f"couldn't dm {guild.owner}, error reason: \n {e}")

    @app_commands.command(name="leave_server", description="[DEV] Leave a server")
    @in_guild()
    async def leave_server(self, interaction: discord.Interaction, guildid: int):
        if interaction.user.id != 188647277181665280:
            return await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)
        guild = self.bot.get_guild(guildid)
        await guild.leave()
        await interaction.response.send_message(f"Left {guild}")

    @app_commands.command(name="blacklist_server", description="[DEV] Blacklist a server")
    @in_guild()
    async def blacklist_server(self, interaction: discord.Interaction, guildid: int):
        if interaction.user.id != 188647277181665280:
            return await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)
        guild = self.bot.get_guild(guildid)
        await Configer.add_to_blacklist(guildid)
        await guild.leave()
        await interaction.response.send_message(f"Blacklisted {guild}")

    @app_commands.command(name="unblacklist_server", description="[DEV] Remove a server from the blacklist")
    @in_guild()
    async def unblacklist_server(self, interaction: discord.Interaction, guildid: int):
        if interaction.user.id != 188647277181665280:
            return await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)
        await Configer.remove_from_blacklist(guildid)
        await interaction.response.send_message(f"Unblacklisted {guildid}")

    @app_commands.command(name="approve_ban", description="Approve a ban")
    @in_guild()
    async def approve_ban(self, interaction: discord.Interaction, wait_id: int):
        if interaction.user.id != 188647277181665280:
            return await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)
        guildid, userid, reason = await Bans().announce_retrieve(wait_id)
        if guildid is None or userid is None or reason is None:
            return await interaction.response.send_message("Waitlist ERROR", ephemeral=True)
        guild = self.bot.get_guild(guildid)
        owner = guild.owner
        user = await self.bot.fetch_user(userid)

        approved_channel = self.bot.get_channel(self.bot.APPROVALCHANNEL)
        banembed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({owner})",
                                 description=f"{reason}")
        try:
            config = await Configer.get(guild.id, "modchannel")
            invite = await guild.get_channel(config).create_invite()
        except discord.Forbidden:
            invite = 'No permission'
        except Exception as e:
            invite = f'No permission/Error'
            logging.error(f"Error creating invite: {e}")
        banembed.set_footer(text=f"Server Invite: {invite} Server Owner: {owner} Banned userid: {user.id} ")
        for guilds in self.bot.guilds:
            if guilds.id == guild.id:
                continue
            if user in guilds.members:
                queue().add(self.inform_server(guilds, banembed))
        await Bans().announce_remove(wait_id)
        await interaction.response.send_message(f"Approved ban for {user.id}", ephemeral=True)
        await approved_channel.send(embed=banembed)

    @app_commands.command(name="checklist", description="[DEV] Manage the checklist, these bans will be checked due to controversial reasons")
    @app_commands.choices(operation=[
        Choice(name="add", value="add"),
        Choice(name="remove", value="remove"),
        Choice(name="list", value="list")
    ])
    @in_guild()
    async def checklist(self, interaction: discord.Interaction, operation: Choice[str], word: str):
        match operation.value:
            case "add":
                await Configer.add_checklist(word)
                await interaction.response.send_message(f"Added {word} to the checklist", ephemeral=True)
            case "remove":
                await Configer.remove_checklist(word)
                await interaction.response.send_message(f"Removed {word} from the checklist", ephemeral=True)
            case "list":
                checklist: list = await Configer.get_checklist()
                l = "\n".join(checklist)
                await interaction.response.send_message(f"Checklist: {l}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(dev(bot))
