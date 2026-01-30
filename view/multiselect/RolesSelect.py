import discord
from discord.utils import get
from typing_extensions import override

from classes.configdata import ConfigData
from classes.permissions import PermissionsCheck
from classes.queue import queue
from database.transactions.ConfigTransactions import ConfigTransactions


class RolesSelect(discord.ui.RoleSelect):

    def __init__(self, placeholder="Select roles", min_values=1, max_values=10):
        super().__init__(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values
        )

    async def callback(self, interaction: discord.Interaction):
        self.values.append(interaction.guild.default_role)
        self.values.append(interaction.guild.me)
        channel = get(interaction.guild.text_channels, name="banwatch-alerts")
        if not channel:
            channel = await interaction.guild.create_text_channel(
                name="banwatch-alerts",
                overwrites={
                    role: discord.PermissionOverwrite(read_messages=True, embed_links=True, read_message_history=True, send_messages=True)
                    for role in self.values
                }
            )
        ConfigTransactions().config_unique_add(interaction.guild.id, "modchannel", channel.id)
        await interaction.response.send_message(f"Mod channel created: {channel.mention}", ephemeral=True)
        queue().add(PermissionsCheck().permission_check(interaction, channel), priority=2)





