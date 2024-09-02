import logging

import discord

max_length = 1800


class NoMessagePermission(Exception):
    """Raised when the bot does not have permission to send a message"""

    def __init__(self, message="Missing permission to send message: ", missing_permissions: list = ()):
        self.message = message
        super().__init__(self.message + ", ".join(missing_permissions))


async def check_missing_permissions(channel: discord.TextChannel, required_permissions: list) -> list:
    """
    Check which permissions are missing for the bot in the specified channel.

    :param channel: The channel to check permissions for.
    :param required_permissions: A list of required permissions to check.
    :return: A list of missing permissions.
    """
    bot_permissions = channel.permissions_for(channel.guild.me)
    missing_permissions = [perm for perm in required_permissions if not getattr(bot_permissions, perm)]
    return missing_permissions


async def send_message(channel: discord.TextChannel, message=None, embed=None, view=None) -> None:
    """Send a message to a channel, if there is no permission it will send an error message to the owner"""
    try:
        logging.debug(f"Sending message to {channel.name}")
        length = 0
        if message is None:
            await channel.send(embed=embed, view=view)
            return
        while length < len(message):
            await channel.send(message[length:length + max_length], embed=embed, view=view)
            length += max_length
    except discord.errors.Forbidden:
        required_perms = ['view_channel', 'send_messages', 'embed_links', 'attach_files']
        missing_perms = await check_missing_permissions(channel, required_perms)
        logging.error(f"Missing permission to send message to {channel.mention} in {channel.guild.name}")
        await channel.guild.owner.send(f"Missing permission to send message to {channel.name}. Check permissions: {', '.join(missing_perms)}", )
        raise NoMessagePermission(missing_permissions=missing_perms)


# noinspection PyUnresolvedReferences
async def send_response(interaction: discord.Interaction, response, ephemeral=False):
    """Send a response to an interaction"""
    try:
        await interaction.response.send_message(response, ephemeral=ephemeral)
    except discord.errors.Forbidden:
        required_perms = ['view_channel', 'send_messages', 'embed_links', 'attach_files']
        missing_perms = await check_missing_permissions(interaction.channel, required_perms)
        logging.error(f"Missing permission to send message to {channel.name}")
        await interaction.guild.owner.send(f"Missing permission to send message to {channel.name}. Check permissions: {', '.join(missing_perms)}", )
        raise NoMessagePermission(missing_permissions=missing_perms)
    except discord.errors.NotFound:
        await interaction.followup.send(
                response,
                ephemeral=ephemeral
        )
