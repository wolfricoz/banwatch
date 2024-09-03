"""This class generates the ban list, with functions to update it, and to check for similar names"""
import logging

import discord
from discord.ext import commands

from classes.cacher import LongTermCache
from classes.configer import Configer
from classes.queue import queue
from classes.support.discord_tools import send_message


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Bans(metaclass=Singleton):
    bans: dict = {}
    old_bans: dict = {}
    guildinvites: dict = {}

    def __init__(self):
        pass

    def is_ready(self):
        """Checks if the ban list is ready"""
        if len(self.bans) > 0:
            print("ready")
            return True
        else:
            print("not ready")
            return False

    async def update(self, bot, override=False):
        """Updates the ban list"""
        guild: discord.Guild
        self.old_bans = self.bans
        Bans().bans = LongTermCache().get_logged_bans()
        if override:
            self.bans = {}
            pass
        for guild in bot.guilds:
            queue().add(Bans().add_guild_bans(bot, guild), priority=0)
            queue().add(Bans().add_guild_invites(guild), priority=0)
        queue().add(Bans().store_bans(), priority=0)

    async def store_bans(self):
        """Stores the bans in the cache"""
        LongTermCache().update_logged_bans(self.bans)

    async def add_guild_invites(self, guild):
        try:
            invite: discord.Invite = (await guild.invites())[0]
        except discord.Forbidden:
            invite: str = "No permission"
        except Exception as e:
            logging.error(f"Error creating invite: {e}")
            invite: str = "No permission/Error"
        await self.add_invite(guild.id, invite)

    async def add_guild_bans(self, bot, guild):
        """Adds the bans from a guild to the ban list"""
        print(f"Adding bans from {guild}")
        try:
            async for entry in guild.bans():
                await self.add_ban(bot, guild, entry.user, entry.reason)
        except discord.Forbidden:
            try:
                await guild.owner.send("[Permission ERROR] I need the ban permission to view the server's ban list. Please give me the ban permission.")
            except discord.Forbidden:
                logging.error(f"Unable to send message to {guild.owner} after trying to inform about missing permissions")

    async def add_ban(self, bot, guild, user, reason):
        """Adds a ban to the ban list"""
        if reason is None or reason == "" or reason.lower == "none" or str(reason).lower().startswith('[hidden]'):
            return
        try:
            if (str(user.id) in self.bans
                    and guild.id in self.bans[f"{user.id}"]
                    and 'reason' in self.bans[f"{user.id}"][f"{guild.id}"]
                    and self.bans[f"{user.id}"][f"{guild.id}"]['reason'] == reason):
                """If the ban is already in the list, do nothing"""
                return
        except KeyError:
            pass

        if str(user.id) in self.bans:
            """If the user is already in the list, add the new ban to the user"""
            self.bans[f"{user.id}"][f"{guild.id}"] = {}
            self.bans[f"{user.id}"][f"{guild.id}"]["name"] = guild.name
            self.bans[f"{user.id}"][f"{guild.id}"]['reason'] = reason
            self.bans[f"{user.id}"]['name'] = user.name
            return

        self.bans[f"{user.id}"] = {}
        self.bans[f"{user.id}"][f"{guild.id}"] = {}
        self.bans[f"{user.id}"][f"{guild.id}"]["name"] = guild.name
        self.bans[f"{user.id}"][f"{guild.id}"]['reason'] = reason
        self.bans[f"{user.id}"]['name'] = user.name

        print(f"Added {user.name} to ban list")

    async def add_invite(self, guildid, invite):
        """Adds a server invite to the invite list"""
        self.guildinvites[f"{guildid}"] = invite

    async def check(self, bot: commands.Bot, memberid: int) -> str or None:
        """checks if user is in banlist"""
        if f"{memberid}" in self.bans:
            sr = await self.search(bot, memberid)
            return sr
        if f"{memberid}" in self.old_bans:
            sr = await self.search(bot, memberid)
            return sr
        return None

    async def search(self, bot, memberid):
        reasons = []
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
        sr = "".join(reasons)
        return sr

    async def send_to_channel(self, channel: discord.TextChannel, sr, memberid: int):
        characters = 0
        while characters < len(sr):
            message = f"{Bans().bans[f'{memberid}']['name']}({memberid}) is banned in: {sr}"
            await send_message(channel, message[characters:characters + 1800])
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
        queue().add(self.send_to_ban_channel(approved_channel, banembed, guild, user, open_thread))

    async def send_to_ban_channel(self, approved_channel, banembed, guild, user, open_thread):
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

    async def search_messages(self, bot, channel: discord.TextChannel, banid: str, reason: str):
        banid = str(banid)
        print(f"checking {channel.name} ({channel.guild.name})")
        try:
            async for message in channel.history():
                if message.author.id != bot.user.id:
                    continue
                if len(message.embeds) < 1:
                    continue
                embed = message.embeds[0]
                # if embed.footer.text:
                #     print(f"checking {message.id} in {channel.name} ({channel.guild.name}) with footer: {embed.footer.text}")

                if embed.footer.text and banid in embed.footer.text:
                    print(f"Found {message.id} in {channel.name} ({channel.guild.name})")
                    queue().add(self.delete_message(message), priority=2)
                    queue().add(channel.send(f"Revoked ban `{embed.title}`! Reason: \n"
                                             f"{reason}"), priority=2)
                    print(f"[revoke_ban] Queued deletion of {message.id} in {channel.name} ({channel.guild.name})")
                    logging.info(f"[revoke_ban] Queued deletion of {message.id} in {channel.name} ({channel.guild.name})")
                    break
        except discord.Forbidden:
            await channel.guild.owner.send(
                    f"Banwatch does not have permission to view chat history or access to the channel in {channel.name} ({channel.guild}). Please give Banwatch the necessary permissions to revoke bans. This is to ensure that"
                    f" the correct information is shared and bans with false information can be removed.")
            logging.error(f"Missing permissions to search messages in {channel.name} ({channel.guild})")

    async def revoke_bans(self, bot, banid, reason):
        for guild in bot.guilds:
            modchannel = await Configer.get(guild.id, "modchannel")
            channel = bot.get_channel(int(modchannel))
            if channel is None:
                continue
            queue().add(self.search_messages(bot, channel, banid, reason), priority=2)
        channel = bot.get_channel(bot.APPROVALCHANNEL)
        queue().add(self.search_messages(bot, channel, banid, reason), priority=2)

