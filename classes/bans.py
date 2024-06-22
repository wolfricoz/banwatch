"This class generates the ban list, with functions to update it, and to check for similar names"
import logging

import discord
from discord.ext import commands

from classes.configer import Configer
from classes.queue import queue


class Bans:
    bans = {}
    guildinvites = {}
    waiting = {}

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
        self.waiting[wait_id] = {}
        self.waiting[wait_id]['guild'] = guildid
        self.waiting[wait_id]['user'] = userid
        self.waiting[wait_id]['reason'] = reason
        return wait_id

    async def announce_remove(self, wait_id):
        """Removes an announcement from waiting list"""
        self.waiting.pop(wait_id)

    async def announce_retrieve(self, wait_id):
        """Retrieves an announcement from waiting list"""
        return self.waiting[wait_id]['guild'], self.waiting[wait_id]['user'], self.waiting[wait_id]['reason']

    async def inform_server(self, bot, guilds, banembed):
        config = await Configer.get(guilds.id, "modchannel")
        modchannel = bot.get_channel(int(config))
        await modchannel.send(embed=banembed)

    async def check_guilds(self, interaction, bot, guild, user, banembed, wait_id):
        approved_channel = bot.get_channel(bot.APPROVALCHANNEL)
        for guilds in bot.guilds:
            if guilds.id == guild.id:
                continue
            if user in guilds.members:
                queue().add(self.inform_server(bot, guilds, banembed))
        await Bans().announce_remove(wait_id)
        if interaction is not None:
            await interaction.message.delete()
        await approved_channel.send(embed=banembed)

    async def create_invite(self, guild: discord.Guild):
        try:
            config = await Configer.get(guild.id, "modchannel")
            invite = await guild.get_channel(config).create_invite()
        except discord.Forbidden:
            invite = 'No permission'
        except Exception as e:
            invite = f'No permission/Error'
            logging.error(f"Error creating invite: {e}")

        return invite