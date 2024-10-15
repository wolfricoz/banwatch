import os

import discord
from discord import app_commands
from discord.ext import commands

from classes.evidence import EvidenceController
from classes.support.discord_tools import await_message


class Evidence(commands.GroupCog, name="evidence"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="add", description="Adds evidence to a user's record")
    @app_commands.checks.has_permissions(ban_members=True)
    async def add(self, interaction: discord.Interaction, user: discord.User):
        """Adds evidence to a user's record"""
        ban_entry: discord.Message
        ban_id = interaction.guild.id + user.id
        evidence_message = f"Please send a message with the evidence you would like to add to {user.name}'s record, this will be added to the ban ID {ban_id} in our support server. \n Type `cancel` to cancel.\n-# By responding to this message you agree to the evidence being stored in our support server."
        evidence = await await_message(interaction, evidence_message)
        channel = self.bot.get_channel(int(os.getenv("APPROVED")))
        await EvidenceController.add_evidence(interaction, evidence, ban_id, channel, user)


async def setup(bot: commands.Bot):
    await bot.add_cog(Evidence(bot))
