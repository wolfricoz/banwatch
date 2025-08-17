import discord
from discord import app_commands
from discord.ext import commands
from discord_py_utilities.messages import send_message, send_response

from classes.access import AccessControl
from classes.configdata import ConfigData
from database.databaseController import BanDbTransactions
from view.buttons.communicationbuttons import CommunicationButtons
from view.modals.inputmodal import send_modal


class ServerMessenger(commands.GroupCog, name="server") :

	def __init__(self, bot: commands.Bot) :
		self.bot = bot

	@app_commands.command(name="message")
	@app_commands.checks.has_permissions(moderate_members=True)
	async def send(self, interaction: discord.Interaction, ban_id: str ) :
		"""Sends a message to the server who owns the ban"""
		staff = AccessControl().access_all(interaction.user.id)

		if interaction.guild.member_count < 250 and not staff:
			await send_response(interaction, f"[Safeguard]You must have at least 250 members to use this command", ephemeral=True)
			return

		ban = BanDbTransactions().get(ban_id, override=staff)
		if ban is None:
			await send_response(interaction, f"Failed to find {ban_id}, does it exist?", ephemeral=True)
			return

		user = self.bot.get_user(ban.uid)
		if user is None:
			user = await self.bot.fetch_user(ban.uid)
		if user == interaction.user:
			await send_response(interaction, f"You can't send a message about your own ban, please use the appeal commands.")
		guild = self.bot.get_guild(ban.gid)
		if guild is None:
			guild = self.bot.fetch_guild(ban.gid)
		content = await send_modal(interaction, "Your message has been sent.")
		conf_mod_channel = ConfigData().get_key_or_none(guild.id, "modchannel")
		if conf_mod_channel is None:
			await send_response(interaction, "This guild does not have banwatch configured", ephemeral=True)
		mod_channel = guild.get_channel(conf_mod_channel)
		embed = discord.Embed(title=f"Message from the staff of {guild.name} regarding ban of {user.name}", description=content, color=discord.Color.green())
		embed.set_footer(text=f"{interaction.guild.id}-{ban_id}")

		await send_message(mod_channel, " ", embed=embed, view=CommunicationButtons())


async def setup(bot: commands.Bot) :
	await bot.add_cog(ServerMessenger(bot))
