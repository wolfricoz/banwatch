import typing
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from classes.bans import Bans
from classes.configer import Configer
from classes.support.discord_tools import send_message, send_response
from database.databaseController import AppealsDbTransactions, BanDbTransactions
from view.buttons.appealbuttons import AppealButtons
from view.modals import inputmodal


class Appeals(commands.GroupCog, name="appeal") :

	def __init__(self, bot: commands.Bot) :
		self.bot = bot

	async def autocomplete_appeal(self, interaction: discord.Interaction, text: str) -> typing.List[
		app_commands.Choice[str]] :
		ban: Bans
		data = []
		bans = BanDbTransactions().get_all_user(interaction.user.id)
		for ban in bans :
			if ban == "name" :
				continue
			data.append(app_commands.Choice(name=ban.guild.name, value=str(ban.gid)))
		if len(data) == 0 :
			data.append(app_commands.Choice(name="No bans", value="None"))

		return data

	@app_commands.command()
	@app_commands.autocomplete(guild=autocomplete_appeal)
	async def create(self, interaction: discord.Interaction, guild: str) :
		appeals_allowed = await Configer.get(int(guild), "allow_appeals")
		if appeals_allowed is False:
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
		config = await Configer.get(guild.id, "modchannel")
		modchannel = self.bot.get_channel(int(config))
		if AppealsDbTransactions().add(ban_id, reason) is False :
			return send_message(interaction.channel, f"Entry for {ban_id} already exists; you've likely already applied.")
		embed = discord.Embed(title=f"Ban appeal for {interaction.user}", description=f"{reason}", timestamp=datetime.now())
		embed.set_footer(text=ban_id)
		await modchannel.send(embed=embed, view=AppealButtons(self.bot, interaction.user))
		await interaction.followup.send(f"Ban appeal sent to moderators of {guild.name}", ephemeral=True)


async def setup(bot: commands.Bot) :
	await bot.add_cog(Appeals(bot))
