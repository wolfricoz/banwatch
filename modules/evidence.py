import discord
from discord import app_commands
from discord.ext import commands
import logging

from classes.bans import Bans
from classes.cacher import LongTermCache
from classes.support.discord_tools import send_response, send_message


class Evidence(commands.GroupCog, name="evidence"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="add", description="Adds evidence to a user's record")
    @app_commands.checks.has_permissions(ban_members=True)
    async def add(self, interaction: discord.Interaction, user: discord.User):
        """Adds evidence to a user's record"""
        logging.info(f"Adding evidence to a {user.name}'s record")
        ban_entry: discord.Message
        ban_id = interaction.guild.id + user.id
        await send_response(interaction,
                            f"Please send a message with the evidence you would like to add to {user.name}'s record, this will be added to the ban ID {ban_id} in our support server. \n Type `cancel` to cancel.\n -# By responding to this message you agree to the evidence being stored in our support server.")
        evidence = await self.bot.wait_for('message', check=lambda m: m.author == interaction.user, timeout=600)
        if evidence.content.lower() == "cancel":
            return
        # if
        logging.info("Evidence received")
        attachments = [await a.to_file() for a in evidence.attachments]
        if LongTermCache().get_ban(ban_id):
            logging.info("Ban ID found in cache")
            approval_channel = self.bot.get_channel(self.bot.BANCHANNEL)
            await send_message(approval_channel,
                               f"Ban ID {ban_id} has been updated with new evidence:\n"
                               f"{evidence.content}", files=attachments)
            await send_message(interaction.channel, f"Proof for {user.name}({user.id}) has been added to the evidence channel.")
            return

        ban_entry, embed = await Bans().find_ban_record(self.bot, ban_id)

        if ban_entry is None:
            await send_response(interaction, f"Ban ID {ban_id} not found.")
            return
        thread = await ban_entry.fetch_thread()
        if thread is None:
            thread = await ban_entry.create_thread(name=f"Evidence for {user.name}({user.id})")

        await thread.send(f"{evidence.content}", files=attachments)


async def setup(bot: commands.Bot):
    await bot.add_cog(Evidence(bot))
