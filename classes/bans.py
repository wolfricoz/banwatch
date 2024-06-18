"This class generates the ban list, with functions to update it, and to check for similar names"
import logging

import discord
from discord.ext import commands


class Bans:
    bans = {}
    guildinvites = {}

    def __init__(self):
        pass

    async def update(self, bot):
        """Updates the ban list"""
        for guild in bot.guilds:
            try:
                async for entry in guild.bans():
                    await self.add_ban(bot, guild, entry.user, entry.reason)
            except discord.Forbidden:
                try:
                    await guild.owner.send("[Permission ERROR] I need the ban permission to view the server's ban list. Please give me the ban permission.")
                except discord.Forbidden:
                    logging.error(f"Unable to send message to {guild.owner} after trying to inform about missing permissions")
        print("List updated")

    async def add_ban(self, bot, guild, user, reason):
        """Adds a ban to the ban list"""
        if reason is None or reason == "" or reason.lower == "none" or str(reason).lower().startswith('[hidden]'):
            return
        if str(user.id) in self.bans:
            self.bans[f"{user.id}"][f"{guild.id}"] = {}
            self.bans[f"{user.id}"][f"{guild.id}"]['reason'] = reason
            self.bans[f"{user.id}"]['name'] = user.name
        else:

            self.bans[f"{user.id}"] = {}
            self.bans[f"{user.id}"][f"{guild.id}"] = {}
            self.bans[f"{user.id}"][f"{guild.id}"]['reason'] = reason
            self.bans[f"{user.id}"]['name'] = user.name


    async def check(self, bot: commands.Bot, memberid: int):
        """checks if user is in banlist"""
        if f"{memberid}" in self.bans:
            print("member in bans")
            reasons = []
            count = 0
            for guild in bot.guilds:
                try:
                    ban = self.bans[f"{memberid}"][f"{guild.id}"]['reason']
                    reasons.append(f"\n{guild}: {ban}"
                                   f"\nOwner: `{guild.owner}` Server: `{guild.name}` invite: <{self.guildinvites[f'{guild.id}']}>")
                    count += 1
                except discord.NotFound:
                    pass
                except Exception as e:
                    pass
            sr = "".join(reasons)

            return sr

    async def send_to_channel(self, channel: discord.TextChannel, sr, memberid: int):
        characters = 0
        while characters < len(sr):
            message = f"{Bans().bans[f'{memberid}']['name']}({memberid}) is banned in: {sr}"
            await channel.send(message[characters:characters + 1800])
            characters += 1800
