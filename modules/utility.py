import typing

import discord
from discord import app_commands
from discord.ext import commands

from classes.bans import Bans
from classes.configer import Configer
from view.buttons.appealbuttons import AppealButtons
from view.modals import inputmodal


class Utility(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command()
    async def support(self, interaction: discord.Interaction):
        await interaction.response.send_message(
                "If you are in need of support, please read our documentation at https://wolfricoz.github.io/banwatch/! You can find our discord link in the documentation. If you still need help, please join our discord server and ask in the support channel.")

    @app_commands.command()
    @app_commands.checks.has_permissions(ban_members=True)
    async def update_ban(self, interaction: discord.Interaction, user: str, reason: str):
        if isinstance(user, str):
            user = await self.bot.fetch_user(int(user))
        if user not in interaction.guild.bans():
            await interaction.response.send_message(f"{user} is not banned in this server")
            return
        try:
            await interaction.guild.unban(user, reason='[silent] Updating ban')
            await interaction.guild.ban(user, reason=reason)
        except discord.NotFound:
            await interaction.response.send_message(f"User {user} not found")
            return
        except discord.Forbidden:
            await interaction.response.send_message(f"Bot does not have permission to ban {user}")
            return
        await interaction.response.send_message(f"Updating ban for {user} for {reason}")

    async def autocomplete_appeal(self, interaction: discord.Interaction, text: str) -> typing.List[app_commands.Choice[str]]:
        data = []
        try:
            bans = Bans().bans[str(interaction.user.id)]
        except KeyError:
            bans = {}
        appeals = await Configer.get_user_appeals(interaction.user.id)


        for ban in bans:

            if appeals is not None and str(ban) in appeals:
                continue
            if ban == "name":
                continue
            data.append(app_commands.Choice(name=bans[str(ban)]['name'], value=str(ban)))
        if len(data) == 0:
            data.append(app_commands.Choice(name="No bans", value="None"))

        return data

    @app_commands.command()
    @app_commands.autocomplete(guild=autocomplete_appeal)
    async def appeal(self, interaction: discord.Interaction, guild: str):
        if guild.lower() == "none":
            await interaction.response.send_message("No bans to appeal", ephemeral=True)
            return
        appeals = await Configer.get_user_appeals(interaction.user.id)

        if appeals is not None and guild in appeals:
            print("already appealed")
            return
        reason = await inputmodal.send_modal(interaction, "Your appeal has been sent to the moderators of the server.")
        guild = self.bot.get_guild(int(guild))
        config = await Configer.get(guild.id, "modchannel")
        modchannel = self.bot.get_channel(int(config))
        embed = discord.Embed(title=f"Ban appeal for {interaction.user}", description=f"{reason}")
        await modchannel.send(embed=embed, view=AppealButtons(self.bot, interaction.user))
        await Configer.add_appeal(interaction.user.id, guild.id, reason)
        await interaction.followup.send(f"Ban appeal sent to moderators of {guild.name}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
