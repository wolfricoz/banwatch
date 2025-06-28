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
	count = 0
	for x in interaction.client.guilds :
		if count >= 24 :
			data.append(app_commands.Choice(name=f"{len(interaction.client.guilds) -24} servers not shown", value=str(0)))
			break
		if current.lower() in x.name.lower() or x.name.lower().startswith(current.lower()) :
			data.append(app_commands.Choice(name=x.name.lower(), value=str(x.id)))
			count += 1

	return data[:25]