import logging

import discord
from discord.ext.commands.help import MISSING

max_length = 1800


class NoMessagePermissionException(Exception):
    """Raised when the bot does not have permission to send a message"""

    def __init__(self, message="Missing permission to send message: ", missing_permissions: list = ()):
        self.message = message
        super().__init__(self.message + ", ".join(missing_permissions))


class NoChannelException(Exception):
    """Raised when the server does not have a channel set to send a message"""

    def __init__(self, message="No channel set or does not exist, check the config or fill in the required arguments."):
        self.message = message


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


async def send_message(channel: discord.TextChannel, message=None, embed=None, view=None, files=None, file=None) -> discord.Message:
    """Send a message to a channel, if there is no permission it will send an error message to the owner"""
    last_message = None
    if channel is None:
        raise NoChannelException
    try:
        length = 0
        if message is None:
            return await channel.send(embed=embed, view=view, files=files)
        while length < len(message):
            last_message = await channel.send(message[length:length + max_length], embed=embed, view=view, files=files)
            length += max_length
        else:
            return last_message
    except discord.errors.Forbidden:
        required_perms = ['view_channel', 'send_messages', 'embed_links', 'attach_files']
        missing_perms = await check_missing_permissions(channel, required_perms)
        logging.error(f"Missing permission to send message to {channel.mention} in {channel.guild.name}")
        await channel.guild.owner.send(f"Missing permission to send message to {channel.name}. Check permissions: {', '.join(missing_perms)}", )
        raise NoMessagePermissionException(missing_permissions=missing_perms)


async def send_response(interaction: discord.Interaction, response, ephemeral=False, view=MISSING, embed=MISSING):
    """Send a response to an interaction"""
    try:

        return await interaction.response.send_message(response, ephemeral=ephemeral, view=view, embed=embed, )
    except discord.errors.Forbidden:
        required_perms = ['view_channel', 'send_messages', 'embed_links', 'attach_files']
        missing_perms = await check_missing_permissions(interaction.channel, required_perms)
        logging.error(f"Missing permission to send message to {interaction.channel.name}")
        await interaction.guild.owner.send(f"Missing permission to send message to {interaction.channel.name}. Check permissions: {', '.join(missing_perms)}", )
        raise NoMessagePermissionException(missing_permissions=missing_perms)
    except discord.errors.NotFound or discord.InteractionResponded:
        try:
            await interaction.followup.send(
                    response,
                    ephemeral=ephemeral,
                    view=view,
                    embed=embed,

            )
        except discord.errors.NotFound:
            await send_message(interaction.channel, response, view=view, embed=embed)
    except Exception:
        return await interaction.channel.send(response, view=view, embed=embed)


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
            logging.error(f"Missing permission to view archived threads in {channel.mention}({channel.name}) in {channel.guild.name}")
    return all_threads


async def ban_member(bans_class, interaction, user, reason, days=1):
    try:
        await bans_class.add_ban(user.id, interaction.guild.id, reason, interaction.user.name)
        await interaction.guild.ban(user, reason=reason, delete_message_days=days)
    except discord.Forbidden:
        error = f"Missing permission to ban user {user.name}({user.id}). Check permissions: ban_members or if the bot is higher in the hierarchy than the user."
        logging.error(error)
        await interaction.channel.send(error)
        raise NoMessagePermissionException(missing_permissions=['ban_members'])


async def await_message(interaction, message) -> discord.Message | bool:
    msg: discord.Message = await send_message(interaction.channel,
                                              message)
    m = await interaction.client.wait_for('message', check=lambda m: m.author == interaction.user, timeout=600)
    await msg.delete()
    if m.content.lower() == "cancel":
        return False
    return m
