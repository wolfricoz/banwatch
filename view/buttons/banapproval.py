import asyncio

import discord
from discord.ui import View

from classes.configer import Configer


class BanApproval(View):

    bot = None
    def __init__(self, bot, guild, user, ban, sleep: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild = guild
        self.user = user
        self.ban = ban
        self.sleep = sleep


    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success)
    async def approve(self, button: discord.ui.Button, interaction: discord.Interaction):
        for guilds in self.bot.guilds:
            if guilds.id == self.guild.id:
                continue
            if self.user in guilds.members:
                await asyncio.sleep(self.sleep)
                config = await Configer.get(guilds.id, "modchannel")
                modchannel = self.bot.get_channel(int(config))
                invites = []
                try:
                    invites = await self.guild.invites()
                # Maybe instead of making an array of invites, have banwatch generate a limited time invite.
                except AttributeError:
                    await self.guild.text_channels[0].send("You have not set a moderation channel")
                except discord.Forbidden:
                    await guilds.owner.send(f"No permission to send a message in {modchannel.mention}")
                except Exception:
                    invites = ["No permission"]
                banembed = discord.Embed(title=f"{self.user} ({self.user.id}) was banned in {self.guild}({self.guild.owner})",
                                            description=f"{self.ban.reason}")
                banembed.set_footer(text=f"{invites[0] if invites else 'No invite'}")

                await modchannel.send(embed=banembed)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger)
    async def deny(self, button: discord.ui.Button, interaction: discord.Interaction):
        pass