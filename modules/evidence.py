import os

import discord
from discord import app_commands
from discord.ext import commands

from classes.evidence import EvidenceController
from classes.support.discord_tools import await_message, send_response
from database.databaseController import ProofDbTransactions
from view.pagination.pagination import Pagination


class Evidence(commands.GroupCog, name="evidence"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="add", description="Adds evidence to a user's record")
    @app_commands.checks.has_permissions(ban_members=True)
    async def add(self, interaction: discord.Interaction, user: discord.User):
        """Adds evidence to a user's record"""
        ban_entry: discord.Message
        ban_id = interaction.guild.id + user.id
        try:
            await interaction.guild.fetch_ban(user)
        except discord.NotFound:
            await send_response(interaction, f"{user.mention} not found in this servers bans")
            return

        evidence_message = f"Please send a message with the evidence you would like to add to {user.name}'s record, this will be added to the ban ID {ban_id} in our support server. \n Type `cancel` to cancel.\n-# By responding to this message you agree to the evidence being stored in our support server.\n\n**Do __not__ use forwarded messages, as these are currently not supported.**"
        evidence = await await_message(interaction, evidence_message)
        channel = self.bot.get_channel(int(os.getenv("APPROVED")))
        await EvidenceController.add_evidence(interaction, evidence, ban_id, user)

    @app_commands.command(name="get", description="Get the proof for an user's ban!")
    @app_commands.checks.has_permissions(ban_members=True)
    async def get(self, interaction: discord.Interaction, user: discord.User = None, ban_id: str = None):
        if user is None and ban_id is None:
            await send_response(interaction, "Please fill in the user or ban_id field to get the user.")

        if ban_id:
            entries = ProofDbTransactions().get(ban_id=ban_id)
            await EvidenceController().send_proof(interaction, entries, ban_id)
            return
        # user goes here
        entries = ProofDbTransactions().get(user_id=user.id)
        await EvidenceController().send_proof(interaction, entries, user.id)

    # Add a way to manage bans, both for staff of a server as well as the banwatch staff
    @app_commands.command(name="manage", description="View evidence and manage evidence")
    @app_commands.checks.has_permissions(ban_members=True)
    async def manage(self, interaction: discord.Interaction, user: discord.User = None, ban_id: str = None):
        if ban_id:
            entries = ProofDbTransactions().get(ban_id=ban_id)
            return
        # user goes here
        entries = ProofDbTransactions().get(user_id=user.id)
        view = Pagination(entries)
        view.interaction = interaction
        await view.send_view()


async def setup(bot: commands.Bot):
    await bot.add_cog(Evidence(bot))
