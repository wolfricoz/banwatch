import asyncio
import os

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from sqlalchemy.testing.plugin.plugin_base import logging

from classes.access import AccessControl
from classes.bans import Bans
from classes.configer import Configer
from classes.queue import queue
from classes.support.discord_tools import send_response, send_message, get_all_threads
from classes.tasks import pending_bans
from database.databaseController import StaffDbTransactions, BanDbTransactions, ServerDbTransactions
from view.modals.inputmodal import send_modal

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


SUPPORT_GUILD = discord.Object(GUILD)


class dev(commands.GroupCog, name="dev"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def inform_server(self, guilds, banembed):
        config = await Configer.get(guilds.id, "modchannel")
        modchannel = self.bot.get_channel(int(config))
        await modchannel.send(embed=banembed)

    @app_commands.command(name="updatecommands", description="[DEV] Unloads and syncs commands again", )
    @in_guild()
    async def update_commands(self, interaction: discord.Interaction):
        queue().add(self.bot.tree.clear_commands(guild=None), priority=2)
        queue().add(self.bot.tree.sync(), priority=2)
        await interaction.response.send_message("Command sync queue, high priority queue.")

    @app_commands.command(name="stats", description="View banwatch's stats!", )
    async def stats(self, interaction: discord.Interaction):
        with open('countbans.txt', 'w'):
            pass

        stats = {
            "servers_total": ServerDbTransactions().count_servers(),
            "bans_total"   : BanDbTransactions().count_bans(),
            "verified_bans": BanDbTransactions().count_bans(result_type="verified"),
            "deleted_bans" : BanDbTransactions().count_bans(result_type="deleted"),
            "hidden_bans"  : BanDbTransactions().count_bans(result_type="hidden"),
            "available"    : BanDbTransactions().count_bans(result_type="available"),
            "queue-status" : queue().status()
        }
        embed = discord.Embed(title="Banwatch's stats")
        for i, v in stats.items():
            embed.add_field(name=i, value=v, inline=False)
        await send_message(interaction.channel, embed=embed)

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

    # @app_commands.command(name="migrate_ban")
    # @in_guild()
    # async def copy(self, interaction: discord.Interaction, channelid: str):
    #     if interaction.user.id != 188647277181665280:
    #         return await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)
    #     await interaction.response.send_message("Migration Started")
    #     channel = self.bot.get_channel(int(channelid))
    #     async for message in channel.history(limit=None, oldest_first=True):
    #         thread = channel.guild.get_thread(message.id)
    #         await asyncio.sleep(2)
    #         timestamp = message.created_at.strftime("%m/%d/%Y")
    #         new = await interaction.channel.send(f"Migrated ban from the old server, sent on {timestamp}:\n{message.content} ", embeds=message.embeds, silent=True)
    #         if thread is not None:
    #             new_thread = await new.create_thread(name=thread.name)
    #             async for msg in thread.history(limit=None, oldest_first=True):
    #                 if msg.content is None and len(msg.attachments) < 1 and len(msg.embeds) < 1:
    #                     continue
    #                 queue().add(new_thread.send(msg.content if len(msg.content) > 0 else "Empty Msg", embeds=msg.embeds, files=[await attachment.to_file() for attachment in msg.attachments], silent=True))

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
        await send_response(interaction, f"Checking threads", ephemeral=True)
        dev_guild: discord.Guild = self.bot.get_guild(self.bot.SUPPORTGUILD)
        all_threads = await get_all_threads(dev_guild)
        for thread in all_threads:
            print(f"checking {thread} in {thread.parent.name}")
            async for message in thread.history(limit=5, oldest_first=True):
                print(message.content)
                if id in message.content:
                    await interaction.followup.send(f"Found in {thread.mention}: {message.jump_url}")
                    return
        await send_message(interaction.channel, "Not found")

    @app_commands.command(name="add_staff", description="[DEV] Adds a staff member to the team")
    @app_commands.choices(role=[Choice(name=x, value=x.lower()) for x in ["Dev", "Rep"]])
    @in_guild()
    async def add_staff(self, interaction: discord.Interaction, user: discord.User, role: Choice[str]):
        StaffDbTransactions().add(user.id, role.value)
        await send_response(interaction, f"Staff member {user.mention} successfully added as a `{role.name}`!")
        AccessControl().reload()

    @app_commands.command(name="amistaff", description="[DEV] check if you're a banwatch staff member.")
    async def amistaff(self, interaction: discord.Interaction):
        return await send_response(interaction, "You are a staff member" if AccessControl().access_all(interaction.user) else "You are not a staff member")


async def setup(bot: commands.Bot):
    await bot.add_cog(dev(bot), guild=SUPPORT_GUILD)