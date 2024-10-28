import os
import typing

import discord
from discord import app_commands
from discord.ext import commands

from classes.access import AccessControl
from classes.support.discord_tools import send_response, send_message
from database.databaseController import ServerDbTransactions

SUPPORT_GUILD = discord.Object(1251639351918727259)


class staff(commands.GroupCog, name="staff"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
    # This doesn't work when limited to one server, only globally?
    async def server_autocompletion(self, interaction: discord.Interaction, current: str) -> typing.List[
        app_commands.Choice[str]]:
        """generates the options for autocomplete."""
        data = []
        for x in interaction.client.guilds:
            if current.lower() in x.name.lower() or current.lower() == x.name.lower():
                data.append(app_commands.Choice(name=x.name.lower(), value=str(x.id)))
        return data

    @app_commands.command(name="servers", description="[staff] View all servers banwatch is in")
    @app_commands.guilds(SUPPORT_GUILD)
    @AccessControl().check_access()
    async def servers(self, interaction: discord.Interaction):
        await send_response(interaction, "Fetching servers, please be patient", ephemeral=True)
        servers = []
        for server in self.bot.guilds:
            info = f"{server.name} ({server.id}) owner: {server.owner.name}({server.owner.id})"
            servers.append(info)
        servers.append(f"For more information, please use the /staff server command")
        result = "\n\n".join(servers)
        with open('servers.txt', 'w') as file:
            file.write(f"I am in {len(self.bot.guilds)} servers:\n")
            file.write(result)
        await send_message(interaction.channel, "Here is a file with all the servers", files=[discord.File(file.name)])
        os.remove(file.name)

    @app_commands.command(name="serverinfo", description="[staff] View server info of a specific server")
    @app_commands.autocomplete(server=server_autocompletion)
    async def serverinfo(self, interaction: discord.Interaction, server: str):
        await send_response(interaction, "Retrieving server data")
        guild = self.bot.get_guild(int(server))
        if guild is None:
            guild = await self.bot.fetch_guild(int(server))
        if guild is None:
            return
        embed = discord.Embed(title=f"{guild.name}'s info")
        server_info = ServerDbTransactions().get(guild.id)
        guild_data = {
            "Owner"        : f"{guild.owner}({guild.owner.id})",
            "User count"   : len([m for m in guild.members if not m.bot]),
            "Channel count": len(guild.channels),
            "Role count"   : len(guild.roles),
            "Created at"   : guild.created_at.strftime("%m/%d/%Y"),
            "bans"         : len(ServerDbTransactions().get_bans(guild.id)),
            "MFA level"    : guild.mfa_level,
            "invite"       : server_info.invite

        }
        for key, value in guild_data.items():
            embed.add_field(name=key, value=value)
        embed.set_footer(text=f"This data should not be shared outside of the support server.")


async def setup(bot: commands.Bot):
    await bot.add_cog(staff(bot), guild=SUPPORT_GUILD)
    # await bot.tree.sync(guild=SUPPORT_GUILD)
