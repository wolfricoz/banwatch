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
                    if entry.reason is None or entry.reason == "" or entry.reason.lower == "none":
                        continue
                    if str(entry.user.id) in self.bans:
                        self.bans[f"{entry.user.id}"][f"{guild.id}"] = {}
                        self.bans[f"{entry.user.id}"][f"{guild.id}"]['reason'] = entry.reason
                        self.bans[f"{entry.user.id}"]['name'] = entry.user.name
                    else:
                        self.bans[f"{entry.user.id}"] = {}
                        self.bans[f"{entry.user.id}"][f"{guild.id}"] = {}
                        self.bans[f"{entry.user.id}"][f"{guild.id}"]['reason'] = entry.reason
                        self.bans[f"{entry.user.id}"]['name'] = entry.user.name
            except discord.Forbidden:
                try:
                    await guild.owner.send("[Permission ERROR] I need the ban permission to view the server's ban list. Please give me the ban permission.")
                except discord.Forbidden:
                    logging.error(f"Unable to send message to {guild.owner} after trying to inform about missing permissions")
            try:
                invites = await guild.invites()
            except discord.Forbidden:
                invites = ['No permission']
            if len(invites) < 1:
                invite = guild.text_channels[0].create_invite()
                invites = [invite]
            self.guildinvites[f"{guild.id}"] = invites[0]
        print("List updated")

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
