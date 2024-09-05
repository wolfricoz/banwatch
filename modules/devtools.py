import asyncio
import os
import random
from abc import ABC

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from sqlalchemy.testing.plugin.plugin_base import logging

from classes.bans import Bans
from classes.configer import Configer
from classes.queue import queue
from classes.support.discord_tools import send_response, send_message, get_all_threads
from classes.tasks import pending_bans
from view.modals.inputmodal import send_modal


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

    def __init__(self, bot: commands.Bot):
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
    async def announce(self, interaction: discord.Interaction):
        message = await send_modal(interaction, "What is the announcement?", "Announcement", 1700)
        if interaction.user.id != 188647277181665280:
            return
        bot = self.bot
        supportguild = bot.get_guild(bot.SUPPORTGUILD)
        support_invite = await Bans().create_invite(supportguild)
        announcement = (f"## BAN WATCH ANNOUNCEMENT"
                        f"\n{message}"
                        f"\n-# You can join our support server by [clicking here to join]({support_invite}). If you have any questions, errors or concerns, please open a ticket in the support server.")

        for guild in self.bot.guilds:
            await asyncio.sleep(1)
            try:
                config = await Configer.get(guild.id, "modchannel")
                configid = int(config)
                channel = self.bot.get_channel(configid)
                await channel.send(announcement)
            except Exception as e:
                try:
                    await guild.owner.send(
                            f"Banwatch could not send the announcement to your modchannel in {guild.name}, please check the mod channel settings. You can setup your modchannel with: ```/config change option:Mod channel channel:```")
                    await guild.owner.send(announcement)
                except Exception as e:
                    await interaction.channel.send(f"Error sending to {guild}({guild.owner}): {e}")

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
    async def blacklist_server(self, interaction: discord.Interaction, guildid: str):
        if interaction.user.id != 188647277181665280:
            return await interaction.response.send_message(f"You are not allowed to use this command.", ephemeral=True)
        guildid = int(guildid)
        guild = self.bot.get_guild(guildid)
        await Configer.add_to_blacklist(guildid)
        await guild.leave()
        await interaction.response.send_message(f"Blacklisted {guild}")

    @app_commands.command(name="unblacklist_server", description="[DEV] Remove a server from the blacklist")
    @in_guild()
    async def unblacklist_server(self, interaction: discord.Interaction, guildid: str):
        if interaction.user.id != 188647277181665280:
            return await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)
        guildid = int(guildid)
        await Configer.remove_from_blacklist(guildid)
        await interaction.response.send_message(f"Unblacklisted {guildid}")

    # blacklist user goes here
    @app_commands.command(name="blacklist_user", description="[DEV] Blacklist a user")
    @in_guild()
    async def blacklist_user(self, interaction: discord.Interaction, userid: str):
        if interaction.user.id != 188647277181665280:
            logging.info(f"{interaction.user.name}({interaction.user.id}) tried to blacklist a user")
            return await send_response(interaction, "You are not allowed to use this command.", ephemeral=True)

            return await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)
        userid = int(userid)
        await Configer.add_to_user_blacklist(userid)
        await send_response(interaction, f"Blacklisted {userid}")

    @app_commands.command(name="unblacklist_user", description="[DEV] Remove a user from the blacklist")
    @in_guild()
    async def unblacklist_user(self, interaction: discord.Interaction, userid: str):
        if interaction.user.id != 188647277181665280:
            logging.info(f"{interaction.user.name}({interaction.user.id}) tried to unblacklist a user")
            return await send_response(interaction, "You are not allowed to use this command.", ephemeral=True)
        userid = int(userid)
        await Configer.remove_from_user_blacklist(userid)
        await send_response(interaction, f"Unblacklisted {userid}")

    @app_commands.command(name="approve_ban", description="Approve a ban")
    @in_guild()
    async def approve_ban(self, interaction: discord.Interaction, wait_id: str):
        if interaction.user.id != 188647277181665280:
            return await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)
        guildid, userid, reason = await Bans().announce_retrieve(self.wait_id)
        if guildid is None or userid is None or reason is None:
            await interaction.followup.send("Waitlist ERROR", ephemeral=True)
            return
        guild = self.bot.get_guild(guildid)
        owner = guild.owner
        user = await self.bot.fetch_user(userid)
        banembed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({owner})",
                                 description=f"{reason}")
        invite = await Bans().create_invite(guild)
        banembed.set_footer(text=f"Server Invite: {invite} Server Owner: {owner} Banned userid: {user.id} ")
        await interaction.followup.send("Approved", ephemeral=True)
        await Bans().check_guilds(interaction, self.bot, guild, user, banembed, wait_id, True)

    @app_commands.command(name="checklist", description="[DEV] Manage the checklist, these bans will be checked due to controversial reasons")
    @app_commands.choices(operation=[
        Choice(name="add", value="add"),
        Choice(name="remove", value="remove"),
        Choice(name="list", value="list")
    ])
    @in_guild()
    async def checklist(self, interaction: discord.Interaction, operation: Choice[str], word: str):
        if interaction.user.id != 188647277181665280:
            return await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)
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

    @app_commands.command(name="migrate_ban")
    @in_guild()
    async def copy(self, interaction: discord.Interaction, channelid: str):
        if interaction.user.id != 188647277181665280:
            return await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)
        await interaction.response.send_message("Migration Started")
        channel = self.bot.get_channel(int(channelid))
        async for message in channel.history(limit=None, oldest_first=True):
            thread = channel.guild.get_thread(message.id)
            await asyncio.sleep(2)
            timestamp = message.created_at.strftime("%m/%d/%Y")
            new = await interaction.channel.send(f"Migrated ban from the old server, sent on {timestamp}:\n{message.content} ", embeds=message.embeds, silent=True)
            if thread is not None:
                new_thread = await new.create_thread(name=thread.name)
                async for msg in thread.history(limit=None, oldest_first=True):
                    if msg.content is None and len(msg.attachments) < 1 and len(msg.embeds) < 1:
                        continue
                    queue().add(new_thread.send(msg.content if len(msg.content) > 0 else "Empty Msg", embeds=msg.embeds, files=[await attachment.to_file() for attachment in msg.attachments], silent=True))

    @app_commands.command(name="testban", description="[DEV] unbans and rebans the test account")
    # @in_guild()
    async def testban(self, interaction: discord.Interaction):
        if interaction.user.id != 188647277181665280:
            return await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)
        user = self.bot.get_user(474365489670389771)
        try:
            await interaction.guild.unban(user, reason="Test unban")
        except Exception:
            pass
        await interaction.guild.ban(user, reason="Test ban")
        await interaction.response.send_message("Test ban complete", ephemeral=True)

    @app_commands.command(name="revokeban", description="[DEV] Revokes a ban message. This does not unban the user.")
    @in_guild()
    async def getembed(self, interaction: discord.Interaction, banid: str, reason: str):
        message = await interaction.response.send_message("Queueing the search for the embed")
        await Bans().revoke_bans(self.bot, banid, reason)

    @app_commands.command(name="pendingbans", description="[DEV] Lists all pending bans")
    @in_guild()
    async def pendingbans(self, interaction: discord.Interaction):
        await pending_bans(self.bot)
        await send_response(interaction, "Checking for pending bans", ephemeral=True)

    @app_commands.command(name="refreshbans", description="[DEV] Refreshes the bans")
    @in_guild()
    async def refreshbans(self, interaction: discord.Interaction):
        await Bans().update(self.bot, override=True)
        await interaction.response.send_message("Bans refresh queued", ephemeral=True)

    @app_commands.command(name="rpsecentrysearch", description="[DEV] Searches the rp security threads for a specific entry")
    @in_guild()
    async def rpseclookup(self, interaction: discord.Interaction, id: str):
        print("testing!")
        await send_response(interaction, f"Checking threads", ephemeral=True)
        dev_guild: discord.Guild = self.bot.get_guild(self.bot.SUPPORTGUILD)
        all_threads = await get_all_threads(dev_guild)
        for thread in all_threads:
            async for message in thread.history(limit=1, oldest_first=True):
                if id in message.content:
                    await interaction.followup.send(f"Found in {thread.mention}: {message.jump_url}")
                    return
        await send_message(interaction.channel, "Not found")


async def setup(bot: commands.Bot):
    await bot.add_cog(dev(bot))
