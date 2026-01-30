import discord
from discord.utils import get
from typing_extensions import override

from classes.configdata import ConfigData
from classes.permissions import PermissionsCheck
from classes.queue import queue
from database.transactions.ConfigTransactions import ConfigTransactions


class ChannelSelect(discord.ui.ChannelSelect):

    def __init__(self, placeholder="Select channels", min_values=1, max_values=1):
        super().__init__(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values
        )

    async def callback(self, interaction: discord.Interaction):
        channel = self.values[0]
        ConfigTransactions().config_unique_add(interaction.guild.id, "modchannel", channel.id)
        await interaction.response.send_message(f"Mod channel set to: {channel.mention}", ephemeral=True)
        channel = interaction.guild.get_channel(channel.id)

        queue().add(PermissionsCheck().permission_check(interaction, channel), priority=2)






