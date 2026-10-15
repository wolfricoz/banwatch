import discord

from classes.config.utils import ConfigUtils
from classes.permissions import PermissionsCheck, channel_problems
from classes.permissions_notice import bot_role_name, format_permissions
from classes.queue import queue
from database.transactions.ConfigTransactions import ConfigTransactions


class ChannelSelect(discord.ui.ChannelSelect):

    def __init__(self, placeholder="Select your mod channel", min_values=1, max_values=1):
        super().__init__(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            channel_types=[discord.ChannelType.text],
        )

    # ============================================================
    async def callback(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(self.values[0].id)
        # Same check as /config change: don't save a channel the bot can't post in.
        missing_required, _ = channel_problems(channel)
        if missing_required:
            return await interaction.response.send_message(
                f"❌ I can't use {channel.mention} as the mod channel yet: I'm missing "
                f"{format_permissions(missing_required)} there.\n"
                f"Open {channel.mention} → **Edit Channel → Permissions**, add **{bot_role_name(interaction.guild)}**, "
                "enable those, then pick the channel again.",
                ephemeral=True)

        ConfigTransactions().config_unique_add(interaction.guild.id, "modchannel", channel.id)
        await interaction.response.send_message(f"Mod channel set to: {channel.mention}", ephemeral=True)

        # The cache still holds the previous modchannel here, so hand log_change the channel it
        # should post in rather than letting it look one up.
        queue().add(ConfigUtils.log_change(interaction.guild, {"modchannel" : channel.mention},
                                           user_name=interaction.user.mention, channel=channel))
        queue().add(PermissionsCheck().permission_check(interaction, channel), priority=2)
