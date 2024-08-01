"This class generates the ban list, with functions to update it, and to check for similar names"
import logging

import discord
from discord.ext import commands

from classes.cacher import LongTermCache
from classes.configer import Configer
from classes.queue import queue


class Bans:
    bans = {}
    guildinvites = {}

    def __init__(self):
        pass

    def is_ready(self):
        """Checks if the ban list is ready"""
        if len(self.bans) > 0:
            return True
        else:
            return False

    async def update(self, bot):
        """Updates the ban list"""
        guild: discord.Guild
        for guild in bot.guilds:
            try:
                async for entry in guild.bans():
                    await self.add_ban(bot, guild, entry.user, entry.reason)
            except discord.Forbidden:
                try:
                    await guild.owner.send("[Permission ERROR] I need the ban permission to view the server's ban list. Please give me the ban permission.")
                except discord.Forbidden:
                    logging.error(f"Unable to send message to {guild.owner} after trying to inform about missing permissions")

            try:
                invite: discord.Invite = (await guild.invites())[0]
            except discord.Forbidden:
                invite: str = "No permission"
            except Exception as e:
                logging.error(f"Error creating invite: {e}")
                invite: str = "No permission/Error"
            await self.add_invite(guild.id, invite)

    async def add_ban(self, bot, guild, user, reason):
        """Adds a ban to the ban list"""
        if reason is None or reason == "" or reason.lower == "none" or str(reason).lower().startswith('[hidden]'):
            return
        if str(user.id) in self.bans:
            self.bans[f"{user.id}"][f"{guild.id}"] = {}
            self.bans[f"{user.id}"][f"{guild.id}"]["name"] = guild.name
            self.bans[f"{user.id}"][f"{guild.id}"]['reason'] = reason
            self.bans[f"{user.id}"]['name'] = user.name
        else:

            self.bans[f"{user.id}"] = {}
            self.bans[f"{user.id}"][f"{guild.id}"] = {}
            self.bans[f"{user.id}"][f"{guild.id}"]["name"] = guild.name
            self.bans[f"{user.id}"][f"{guild.id}"]['reason'] = reason
            self.bans[f"{user.id}"]['name'] = user.name

    async def add_invite(self, guildid, invite):
        """Adds a server invite to the invite list"""
        self.guildinvites[f"{guildid}"] = invite

    async def check(self, bot: commands.Bot, memberid: int):
        """checks if user is in banlist"""
        if f"{memberid}" in self.bans:
            reasons = []
            count = 0
            for ban in self.bans[f"{memberid}"]:
                if ban == "name":
                    continue
                guild = bot.get_guild(int(ban))
                try:
                    print(f"guild: {guild}")
                    invite = self.guildinvites[f"{guild.id}"]
                except KeyError:
                    invite = "No permission"
                reasons.append(f"\n{guild}: {self.bans[f'{memberid}'][f'{ban}']['reason']}"
                               f"\nOwner: `{guild.owner}` Server: `{guild.name}` Invite: `{invite}`\n")
                count += 1

            sr = "".join(reasons)

            return sr

    async def send_to_channel(self, channel: discord.TextChannel, sr, memberid: int):
        characters = 0
        while characters < len(sr):
            message = f"{Bans().bans[f'{memberid}']['name']}({memberid}) is banned in: {sr}"
            await channel.send(message[characters:characters + 1800])
            characters += 1800

    async def announce_add(self, guildid, userid, reason):
        """Creates an announcement in waiting list"""
        wait_id = guildid + userid

        ban_info = {
            "guild" : guildid,
            "user"  : userid,
            "reason": reason
        }
        LongTermCache().add_ban(wait_id, ban_info)
        return wait_id

    async def announce_remove(self, wait_id):
        """Removes an announcement from waiting list"""
        if not LongTermCache().remove_ban(wait_id):
            raise Exception("Wait ID not found")

    async def announce_retrieve(self, wait_id):
        """Retrieves an announcement from waiting list"""
        ban_info = LongTermCache().get_ban(wait_id)
        if not ban_info:
            raise Exception("Wait ID not found")
        return ban_info['guild'], ban_info['user'], ban_info['reason']

    async def inform_server(self, bot, guilds, banembed):
        config = await Configer.get(guilds.id, "modchannel")
        modchannel = bot.get_channel(int(config))
        await modchannel.send(embed=banembed)

    async def check_guilds(self, interaction, bot, guild, user, banembed, wait_id, open_thread=False):
        approved_channel = bot.get_channel(bot.APPROVALCHANNEL)
        for guilds in bot.guilds:
            if guilds.id == guild.id:
                continue
            if user in guilds.members:
                queue().add(self.inform_server(bot, guilds, banembed))
        await Bans().announce_remove(wait_id)
        if interaction is not None:
            await interaction.message.delete()
        approved_message = await approved_channel.send(embed=banembed)
        if not open_thread:
            return
        guild_owner = guild.owner
        thread = await approved_message.create_thread(name=f"Ban approval for {user.name}")
        await thread.send(f"Please provide the proof of the ban here {guild_owner.mention}")
        await guild_owner.send(
                f"Your ban for {user.name} has been approved and has been broadcasted, please provide the proof of the ban in the thread {thread.mention} in our support server. Not in our support server? Do the /support command to get the link!")

    async def create_invite(self, guild: discord.Guild):
        try:
            config = await Configer.get(guild.id, "modchannel")
            invite = await guild.get_channel(config).create_invite(max_age=604800)
        except discord.Forbidden:
            invite = 'No permission'
        except Exception as e:
            invite = f'No permission/Error'
            logging.error(f"Error creating invite: {e}")

        return invite

    async def delete_message(self, message):
        print(f"deleting {message.id}")
        await message.delete()

    async def search_messages(self, bot, interaction: discord.Interaction, channel: discord.TextChannel, banid: str, reason: str):
        count = 0
        banid = str(banid)
        print(f"sending {channel} in {channel.guild}")
        async for message in channel.history(limit=100):
            if message.author.id != bot.user.id:
                continue
            if len(message.embeds) < 1:
                continue
            embed = message.embeds[0]
            if embed.footer.text and banid in embed.footer.text:
                queue().add(self.delete_message(message))
                queue().add(channel.send(f"Revoked ban `{embed.title}`! Reason: \n"
                                         f"{reason}"))
                count += 1
        if interaction is not None:
            await interaction.followup.send(f"Deleted {count} messages in {channel.name} ({channel.guild.name})")
        logging.info(f"[revoke_ban] Deleted {count} messages in {channel.name} ({channel.guild.name})")

    async def revoke_bans(self, bot, banid, reason, interaction = None):
        for guild in bot.guilds:
            modchannel = await Configer.get(guild.id, "modchannel")
            if modchannel is None:
                continue
            channel = bot.get_channel(int(modchannel))
            queue().add(self.search_messages(bot, interaction, channel, banid, reason))
        channel = bot.get_channel(bot.APPROVALCHANNEL)
        queue().add(self.search_messages(bot, interaction, channel, banid, reason))
