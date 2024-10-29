import logging
import re

import discord
from discord.ui import View

from classes.support.discord_tools import ban_member, send_message, send_response
from database.current import Proof
from database.databaseController import BanDbTransactions, ProofDbTransactions


class BanInform(View):
    bot = None

    def __init__(self, ban_class) :
        super().__init__(timeout=None)
        self.ban_class = ban_class

    async def get_ban_id(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        match = re.search(r'ban ID: (\w+)', embed.footer.text)
        return match.group(1) if match else None

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.success, custom_id="ban_user")
    async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ban_id = await self.get_ban_id(interaction)
        print(ban_id)
        if ban_id is None:
            logging.error(f"Could not find ban id in {interaction.guild.name}.")
            await send_response(interaction, f"[REGEX ERROR] Could not retrieve ban_id!")
        entry = BanDbTransactions().get(ban_id)
        user = interaction.client.get_user(entry.uid)
        guild = interaction.client.get_guild(entry.gid)
        reason = f"Cross-ban from {guild.name} with ban id: {ban_id}"
        await ban_member(self.ban_class, interaction, user, reason, days=0)
        await send_response(interaction, f"Banning user")
        await interaction.message.delete()

    @discord.ui.button(label="view evidence", style=discord.ButtonStyle.primary, custom_id="evidence")
    async def evidence(self, interaction: discord.Interaction, button: discord.ui.Button):
        ban_id = await self.get_ban_id(interaction)
        entries = ProofDbTransactions().get(ban_id=ban_id)
        await self.send_proof(interaction, entries, ban_id)

    async def retrieve_proof(self, evidence: Proof):
        """Gets image from discord CDN and then creates a discord.File"""
        if len(evidence.get_attachments()) <= 0:
            return None
        attachments = []
        for i, url in enumerate(evidence.get_attachments()):
            response = requests.get(url, stream=True)
            if response.status_code != 200:
                continue
            image_data = io.BytesIO(response.content)
            image_data.seek(0)
            attachments.append(discord.File(image_data, filename=f"image_{i}.jpg"))
        return attachments

    async def send_proof(self, interaction, entries, ban_id: int):
        if not entries:
            await send_response(interaction, f"Ban for {ban_id} not found!")
            return
        await send_response(interaction, f"Succesfully retrieved proof!", ephemeral=True)
        await send_message(interaction.channel, f"## __Proof for {ban_id}__")
        evidence: Proof
        for evidence in entries:
            attachments = await self.retrieve_proof(evidence)
            content = (f"**{evidence.ban_id}**:"
                       f"\n**ban reason**: {evidence.ban.reason}"
                       f"\n**Provided Proof**: {evidence.proof}")
            await send_message(interaction.channel, content, files=attachments)
