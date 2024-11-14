import typing

import discord
from discord import app_commands

from database.current import Bans
from database.databaseController import BanDbTransactions


async def autocomplete_appeal(interaction: discord.Interaction, text: str) -> typing.List[
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


async def autocomplete_guild(interaction: discord.Interaction, current: str) -> typing.List[
	app_commands.Choice[str]] :
	"""generates the options for autocomplete."""
	data = []
	for x in interaction.client.guilds :
		if current.lower() in x.name.lower() or current.lower() == x.name.lower() :
			data.append(app_commands.Choice(name=x.name.lower(), value=str(x.id)))
	return data