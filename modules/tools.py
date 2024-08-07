import asyncio

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

from classes.bans import Bans
from view.modals.inputmodal import send_modal


class Tools(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def ban_user(self, interaction: discord.Interaction, user: discord.User, ban_type, reason_modal):
        if interaction.guild is None:
            await interaction.channel.send("This command can only be used in a server")
            return
        if user.id == interaction.user.id:
            await interaction.channel.send("You can't ban yourself")
            return
        if user.id == self.bot.user.id:
            await interaction.channel.send("I can't ban myself")
            return
        if user.id == interaction.guild.owner_id:
            await interaction.channel.send("You can't ban the owner of the server")
            return

        reason = f"{ban_type}{reason_modal}"
        await interaction.guild.ban(user, reason=reason)
        # await interaction.channel.send(f"DEBUG: BAN FUNCTION DISABLED FOR TESTING.`")
        embed = discord.Embed(title=f"{user.name}", description=f"{reason}", color=discord.Color.red())
        await interaction.channel.send(embed=embed)
        if ban_type == "[silent]" or ban_type == "[hidden]":
            return
        await self.dm_user(interaction, reason_modal, user)

    async def dm_user(self, interaction, reason_modal, user):
        try:
            await user.send(f"You have been banned from {interaction.guild.name} for `{reason_modal}`")
        except discord.errors.Forbidden:
            pass

    @app_commands.command(name="ban", description="Bans a user from the server")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.choices(ban_type=[
        Choice(name="Normal", value=""),
        Choice(name="Silent", value="[silent]"),
        Choice(name="Hidden", value="[hidden]")
    ])
    async def ban(self, interaction: discord.Interaction, user: discord.User, ban_type: Choice[str] = ""):
        """Bans a user from the server"""
        if isinstance(ban_type, Choice):
            ban_type = ban_type.value
        reason_modal = await send_modal(interaction, "What is the reason for the ban?", "Ban Reason")
        await self.ban_user(interaction, user, ban_type, reason_modal)

    @app_commands.command(name="mass_ban", description="bans multiple users, separated by a space")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.choices(ban_type=[
        Choice(name="Normal", value=""),
        Choice(name="Silent", value="[silent]"),
        Choice(name="Hidden", value="[hidden]")
    ])
    async def mass_ban(self, interaction: discord.Interaction, users: str, ban_type: Choice[str] = ""):
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
            await self.ban_user(interaction, user, ban_type, reason_modal)

    @app_commands.command(name="unban", description="Unbans a user from the server")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user: discord.User):
        """Unbans a user from the server"""
        await interaction.guild.unban(user)
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
            except:
                await interaction.channel.send(f"An error occurred while fetching user with id {user_id}, please unban them manually")
                continue
            try:
                await interaction.guild.unban(user)
            except discord.errors.NotFound:
                await interaction.channel.send(f"user with id {user_id} is not banned")
                continue
            embed = discord.Embed(title=f"{user.name} unbanned", color=discord.Color.green())
            await interaction.channel.send(embed=embed)

    @app_commands.command(name="reban", description="unbans and rebans a user to update the reason")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.choices(ban_type=[
        Choice(name="Normal", value=""),
        Choice(name="Silent", value="[silent]"),
        Choice(name="Hidden", value="[hidden]")
    ])
    async def reban(self, interaction: discord.Interaction, user: discord.User, ban_type: Choice[str] = ""):
        """Bans a user from the server"""
        if isinstance(ban_type, Choice):
            ban_type = ban_type.value
        reason_modal = await send_modal(interaction, "What is the reason for the ban?", "Ban Reason")
        try:
            await interaction.guild.unban(user)
        except discord.errors.NotFound:
            pass
        await self.ban_user(interaction, user, ban_type, reason_modal)

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


async def setup(bot: commands.Bot):
    await bot.add_cog(Tools(bot))
