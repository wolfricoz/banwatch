import logging

import discord
from discord.utils import get
from discord_py_utilities.permissions import check_missing_guild_permissions

from classes.config.utils import ConfigUtils
from classes.permissions import PermissionsCheck, REQUIRED_CHANNEL_PERMS
from classes.permissions_notice import bot_role_name, format_permissions
from classes.queue import queue
from database.transactions.ConfigTransactions import ConfigTransactions

# What the bot and the chosen staff roles get in the channel it creates.
STAFF_OVERWRITE = discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True,
                                              attach_files=True, read_message_history=True)


def alert_channel_overwrites(guild: discord.Guild, staff_roles) -> dict :
    """Private channel: hidden from @everyone, open to the chosen staff roles and the bot."""
    overwrites = {guild.default_role : discord.PermissionOverwrite(view_channel=False)}
    for role in staff_roles :
        if role != guild.default_role :
            overwrites[role] = STAFF_OVERWRITE
    overwrites[guild.me] = STAFF_OVERWRITE
    return overwrites


class RolesSelect(discord.ui.RoleSelect):

    def __init__(self, placeholder="Select the staff roles that should see Banwatch alerts", min_values=1, max_values=10):
        super().__init__(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values
        )

    # ============================================================
    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        channel = get(guild.text_channels, name="banwatch-alerts")
        if not channel:
            # Discord only lets a bot grant channel permissions it already has, so check all of them.
            missing = check_missing_guild_permissions(guild, ["manage_channels", *REQUIRED_CHANNEL_PERMS])
            if missing:
                return await interaction.response.send_message(
                    f"❌ I can't create the alerts channel: I'm missing {format_permissions(missing)} server-wide.\n"
                    f"Enable them under **Server Settings → Roles → {bot_role_name(guild)}** and try again, "
                    "or use **Manual Setup** to pick an existing channel instead.",
                    ephemeral=True)
            try:
                channel = await guild.create_text_channel(name="banwatch-alerts",
                                                          overwrites=alert_channel_overwrites(guild, self.values))
            except discord.Forbidden as e:
                logging.info(f"Could not create banwatch-alerts in {guild.name}({guild.id}): {e}")
                return await interaction.response.send_message(
                    "❌ Discord didn't let me create the alerts channel. Make sure my role "
                    f"**{bot_role_name(guild)}** has **Manage Channels**, or use **Manual Setup** to pick an "
                    "existing channel.",
                    ephemeral=True)
        ConfigTransactions().config_unique_add(guild.id, "modchannel", channel.id)
        await interaction.response.send_message(f"Mod channel created: {channel.mention}", ephemeral=True)
        # The cache still holds the previous modchannel here, so hand log_change the channel it
        # should post in rather than letting it look one up.
        queue().add(ConfigUtils.log_change(guild, {"modchannel" : channel.mention},
                                           user_name=interaction.user.mention, channel=channel))
        queue().add(PermissionsCheck().permission_check(interaction, channel), priority=2)
