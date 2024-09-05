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


async def send_message(channel: discord.TextChannel, message=None, embed=None, view=None) -> discord.Message:
    """Send a message to a channel, if there is no permission it will send an error message to the owner"""
    last_message = None
    try:
        length = 0
        if message is None:
            return await channel.send(embed=embed, view=view)
        while length < len(message):
            last_message = await channel.send(message[length:length + max_length], embed=embed, view=view)
            length += max_length
        else:
            return last_message
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
        return await interaction.response.send_message(response, ephemeral=ephemeral)
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

async def get_all_threads(guild: discord.Guild):
    """Get all threads in a guild"""
    all_threads = []
    for thread in guild.threads:
        all_threads.append(thread)
    for channel in guild.text_channels:
        try:
            async for athread in channel.archived_threads():
                all_threads.append(athread)
        except discord.errors.Forbidden:
            pass
    return all_threads