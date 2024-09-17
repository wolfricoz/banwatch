import asyncio

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from discord.webhook.async_ import interaction_response_params

from classes.bans import Bans
from classes.support.discord_tools import send_response
from view.modals.inputmodal import send_modal


class Evidence(commands.GroupCog , name="evidence"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="add", description="Adds evidence to a user's record")
    @app_commands.checks.has_permissions(ban_members=True)
    async def add(self, interaction: discord.Interaction, user: discord.User):
        """Adds evidence to a user's record"""
        ban_entry: discord.Message
        ban_id = interaction.guild.id + user.id
        await send_response(interaction, f"Please send a message with the evidence you would like to add to {user.name}'s record, this will be added to the ban ID {ban_id} in our support server. \n Type `cancel` to cancel.")
        evidence = await self.bot.wait_for('message', check=lambda m: m.author == interaction.user, timeout=600)
        if evidence.content.lower() == "cancel":
            return

        ban_entry, embed = await Bans().find_ban_record(self.bot, ban_id)
        if ban_entry is None:
            await send_response(interaction, f"Ban ID {ban_id} not found.")
            return
        thread = await ban_entry.fetch_thread()
        if thread is None:
            thread = await ban_entry.create_thread(name=f"Evidence for {user.name}({user.id})")

        await thread.send(f"{evidence.content}", files=[await a.to_file() for a in evidence.attachments])
async def setup(bot: commands.Bot):
    await bot.add_cog(Evidence(bot))
