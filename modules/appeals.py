import os
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands
from discord_py_utilities.messages import send_message, send_response

from classes.access import AccessControl
from classes.autocorrect import autocomplete_appeal
from classes.configdata import ConfigData
from database.databaseController import AppealsDbTransactions, BanDbTransactions
from view.buttons.appealbuttons import AppealButtons
from view.modals import inputmodal


class Appeals(commands.GroupCog, name="appeal") :

	def __init__(self, bot: commands.Bot) :
		self.bot = bot



	@app_commands.command(description="You can use this command to appeal a ban")
	@app_commands.autocomplete(guild=autocomplete_appeal)
	@AccessControl().check_blacklist()
	async def create(self, interaction: discord.Interaction, guild: str) :
		appeals_allowed = ConfigData().get_key_or_none(int(guild), "allow_appeals")
		if appeals_allowed is False or appeals_allowed is None :
			return await send_response(interaction, "This server does not allow appeals.")
		if guild.lower() == "none" :
			await interaction.response.send_message("No bans to appeal", ephemeral=True)
			return
		ban_id = interaction.user.id + int(guild)
		appeal = AppealsDbTransactions().exist(ban_id)
		if appeal :
			return await send_response(interaction, "You have already appealed to this server.")
		reason = await inputmodal.send_modal(interaction, "Your appeal has been sent to the moderators of the server.")
		guild = self.bot.get_guild(int(guild))
		config = ConfigData().get_key(guild.id, "modchannel")
		modchannel = self.bot.get_channel(int(config))
		if AppealsDbTransactions().add(ban_id, reason) is False :
			return send_message(interaction.channel, f"Entry for {ban_id} already exists; you've likely already applied.")
		embed = discord.Embed(title=f"Ban appeal for {interaction.user}", description=f"{reason}", timestamp=datetime.now())
		embed.set_footer(text=ban_id)
		await modchannel.send(embed=embed, view=AppealButtons())
		await interaction.followup.send(f"Ban appeal sent to moderators of {guild.name}", ephemeral=True)

	@app_commands.command(description="Report a harmful ban here!")
	@app_commands.autocomplete(guild=autocomplete_appeal)
	@AccessControl().check_blacklist()
	async def report(self, interaction: discord.Interaction, guild: str) :
		if guild.lower() == "none" :
			await interaction.response.send_message("No bans to report", ephemeral=True)
			return
		appeals_allowed = ConfigData().get_key_or_none(int(guild), "allow_appeals")
		if appeals_allowed is not False or appeals_allowed is not None :
			appeal = AppealsDbTransactions().exist(interaction.user.id + int(guild))
			if not appeal:
				return await send_response(interaction, "You must appeal your ban with the server; please only report bans after all possible appeal options have been exhausted.")
		reason = await inputmodal.send_modal(interaction,
		                                     "Thank you for the report, we will investigate this and get back to you.")
		ban_id = interaction.user.id + int(guild)
		guild = self.bot.get_guild(int(guild))
		ban = BanDbTransactions().get(ban_id, override=True)
		staff_channel = self.bot.get_channel(int(os.getenv("BANS")))
		embed = discord.Embed(title=f"{interaction.user.name} wants to report {ban_id}", description=reason)
		embed.add_field(name=f"{interaction.user.name}({interaction.user.id}) banned in {guild.name}({guild.id})",
		                value=ban.reason)
		await send_message(staff_channel, embed=embed)


async def setup(bot: commands.Bot) :
	await bot.add_cog(Appeals(bot))
