import asyncio

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

from classes.bans import Bans
from classes.support.discord_tools import send_message, send_response, ban_member
from view.modals.inputmodal import send_modal


class Tools(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def ban_user(self, interaction: discord.Interaction, user: discord.User, ban_type, reason_modal, inform=True, clean=False):
        if interaction.guild is None:
            await send_message(interaction.channel, "This command can only be used in a server")
            return
        if user.id == interaction.user.id:
            await send_message(interaction.channel, "You can't ban yourself")
            return
        if user.id == self.bot.user.id:
            await send_message(interaction.channel, "I can't ban myself")
            return
        if user.id == interaction.guild.owner_id:
            await send_message(interaction.channel, "You can't ban the owner of the server")
            return
        if ban_type == "[silent]" or ban_type == "[hidden]":
            inform = False

        reason = f"{ban_type}{reason_modal}"
        await ban_member(interaction, user, reason, days=1 if clean else 0)
        # await interaction.channel.send(f"DEBUG: BAN FUNCTION DISABLED FOR TESTING.`")
        embed = discord.Embed(title=f"{user.name} ({user.id}) banned!", description=f"{reason}", color=discord.Color.red())
        embed.set_footer(text=f"Moderator: {interaction.user.name}, was the user informed? {'Yes' if inform else 'No'}")
        await send_message(interaction.channel, embed=embed)
        if not inform:
            return
        await self.dm_user(interaction, reason_modal, user)

    async def dm_user(self, interaction, reason_modal, user):
        try:
            await user.send(f"You have been banned from {interaction.guild.name} for `{reason_modal}`")
        except discord.errors.Forbidden:
            pass

    @app_commands.command(name="ban", description="Bans a user from the server, by default informs the user.")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.choices(ban_type=[
        Choice(name="Normal", value=""),
        Choice(name="Silent", value="[silent]"),
        Choice(name="Hidden", value="[hidden]")
    ])
    async def ban(self, interaction: discord.Interaction, user: discord.User, ban_type: Choice[str] = "", inform: bool = True, clean: bool = False):
        """Bans a user from the server"""
        if isinstance(ban_type, Choice):
            ban_type = ban_type.value
        reason_modal = await send_modal(interaction, "What is the reason for the ban?", "Ban Reason")
        await self.ban_user(interaction, user, ban_type, reason_modal, inform=inform, clean=clean)

    @app_commands.command(name="mass_ban", description="bans multiple users, separated by a space")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.choices(ban_type=[
        Choice(name="Normal", value=""),
        Choice(name="Silent", value="[silent]"),
        Choice(name="Hidden", value="[hidden]")
    ])
    async def mass_ban(self, interaction: discord.Interaction, users: str, ban_type: Choice[str] = "", inform: bool = True, clean: bool = False):
        """Bans a user from the server"""
        if isinstance(ban_type, Choice):
            ban_type = ban_type.value
        user_list = users.split(" ")
        reason_modal = await send_modal(interaction, "What is the reason for the ban?", "Ban Reason")
        for user_id in user_list:
            await asyncio.sleep(1)
            try:
                user = await self.bot.fetch_user(int(user_id))
            except discord.errors.NotFound:
                await interaction.channel.send(f"User with id {user_id} not found")
                continue
            except:
                await interaction.channel.send(f"An error occurred while fetching user with id {user_id}, please ban them manually")
                continue
            await self.ban_user(interaction, user, ban_type, reason_modal, inform=inform, clean=clean)

    @app_commands.command(name="unban", description="Unbans a user from the server")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user: discord.User):
        """Unbans a user from the server"""

        try:
            await interaction.guild.unban(user)
        except discord.NotFound:
            return await send_message(interaction.channel, "User is not banned/cannot be found")
        embed = discord.Embed(title=f"{user.name} unbanned", color=discord.Color.green())
        await interaction.channel.send(embed=embed)

    @app_commands.command(name="mass_unban", description="Unbans multiple users, separated by a space")
    @app_commands.checks.has_permissions(ban_members=True)
    async def mass_unban(self, interaction: discord.Interaction, users: str):
        """Unbans a user from the server"""
        await interaction.response.send_channel(f"Unbanning {users}", ephemeral=True)
        user_list = users.split(" ")
        for user_id in user_list:
            await asyncio.sleep(1)
            try:
                user = await self.bot.fetch_user(int(user_id))
            except discord.errors.NotFound:
                await interaction.channel.send(f"User with id {user_id} not found")
                continue
            except Exception:
                await interaction.channel.send(f"An error occurred while fetching user with id {user_id}, please unban them manually")
                continue
            try:
                await interaction.guild.unban(user)
            except discord.errors.NotFound:
                await interaction.channel.send(f"user with id {user_id} is not banned")
                continue
            embed = discord.Embed(title=f"{user.name} unbanned", color=discord.Color.green())
            await interaction.channel.send(embed=embed)

    @app_commands.command(name="reban", description="unbans and rebans a user to update the reason. This does not inform the user.")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.choices(ban_type=[
        Choice(name="Normal", value=""),
        Choice(name="Silent", value="[silent]"),
        Choice(name="Hidden", value="[hidden]")
    ])
    async def reban(self, interaction: discord.Interaction, user: discord.User, ban_type: Choice[str] = "", reason: str = "Ban being updated using /reban"):
        """Bans a user from the server"""
        if isinstance(ban_type, Choice):
            ban_type = ban_type.value
        reason_modal = await send_modal(interaction, "What is the reason for the ban?", "Ban Reason")
        try:
            await interaction.guild.unban(user, reason=reason)
        except discord.errors.NotFound:
            pass
        try:
            await self.ban_user(interaction, user, ban_type, reason_modal, inform=False)
        except discord.Forbidden:
            await send_response(interaction, "I don't have permission to ban this user")

    @app_commands.command(name="kick", description="Kicks a user from the server and informs them with a DM. you can also choose to reinvite them.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, user: discord.User, reinvite: bool = False):
        """Kicks a user from the server"""
        await interaction.guild.kick(user)

        reason_modal = send_modal(interaction, "What is the reason for the kick?", "Kick Reason")
        reason = reason_modal
        if reinvite:
            invite = await Bans().create_invite(interaction.guild)
            reason = f"{reason}\n\nReinvite link: {invite}"

        await self.dm_user(interaction, reason, user)
        embed = discord.Embed(title=f"{user.name} kicked", description=reason, color=discord.Color.green())
        await interaction.channel.send(embed=embed)

    @app_commands.command(name="export_bans", description="Exports all guild bans to a text file and sends it to the channel.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def export_bans(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # Fetch all bans
        bans = interaction.guild.bans()

        # Write bans to a text file
        with open("bans.txt", "w", encoding='utf-16') as file:
            async for ban_entry in bans:
                user = ban_entry.user
                reason = ban_entry.reason if ban_entry.reason else "No reason provided"
                file.write(f"User: {user} (ID: {user.id}) - Reason: {reason}\n")
        # Send the file to the channel
        await interaction.followup.send("Here are all your bans!", file=discord.File("bans.txt"))


async def setup(bot: commands.Bot):
    await bot.add_cog(Tools(bot))
