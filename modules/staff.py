import os
import typing

import discord
from discord import app_commands
from discord.ext import commands

from classes.access import AccessControl
from classes.evidence import EvidenceController
from classes.support.discord_tools import await_message, send_message, send_response
from database.databaseController import BanDbTransactions, ServerDbTransactions

GUILD = int(os.getenv("GUILD"))


class staff(commands.GroupCog, name="staff") :

	def __init__(self, bot: commands.Bot) :
		self.bot = bot

	async def server_autocompletion(self, interaction: discord.Interaction, current: str) -> typing.List[
		app_commands.Choice[str]] :
		"""generates the options for autocomplete."""
		data = []
		for x in interaction.client.guilds :
			if current.lower() in x.name.lower() or current.lower() == x.name.lower() :
				data.append(app_commands.Choice(name=x.name.lower(), value=str(x.id)))
		return data

	@app_commands.command(name="servers", description="[staff] View all servers banwatch is in")
	@app_commands.guilds(GUILD)
	@AccessControl().check_access()
	async def servers(self, interaction: discord.Interaction) :
		await send_response(interaction, "Fetching servers, please be patient", ephemeral=True)
		servers = []
		for server in self.bot.guilds :
			info = f"{server.name} ({server.id}) owner: {server.owner.name}({server.owner.id})"
			servers.append(info)
		servers.append(f"For more information, please use the /staff server command")
		result = "\n\n".join(servers)
		with open('servers.txt', 'w') as file :
			file.write(f"I am in {len(self.bot.guilds)} servers:\n")
			file.write(result)
		await send_message(interaction.channel, "Here is a file with all the servers", files=[discord.File(file.name)])
		os.remove(file.name)

	@app_commands.command(name="serverinfo", description="[staff] View server info of a specific server")
	@app_commands.guilds(GUILD)
	@app_commands.autocomplete(server=server_autocompletion)
	@AccessControl().check_access()
	async def serverinfo(self, interaction: discord.Interaction, server: str) :
		await send_response(interaction, "Retrieving server data")
		guild = self.bot.get_guild(int(server))
		if guild is None :
			guild = await self.bot.fetch_guild(int(server))
		if guild is None :
			return
		embed = discord.Embed(title=f"{guild.name}'s info")
		server_info = ServerDbTransactions().get(guild.id)
		guild_data = {
			"Owner"         : f"{guild.owner}({guild.owner.id})",
			"User count"    : len([m for m in guild.members if not m.bot]),
			"Bot count"     : len([m for m in guild.members if m.bot]),
			"Channel count" : len(guild.channels),
			"Role count"    : len(guild.roles),
			"Created at"    : guild.created_at.strftime("%m/%d/%Y"),
			"bans"          : len(ServerDbTransactions().get_bans(guild.id)),
			"MFA level"     : guild.mfa_level,
			"invite"        : server_info.invite

		}
		for key, value in guild_data.items() :
			embed.add_field(name=key, value=value, inline=False)
		embed.set_footer(text=f"This data should not be shared outside of the support server.")
		await send_message(interaction.channel, embed=embed)

	@app_commands.command(name="userinfo", description="[Staff] View user information")
	@AccessControl().check_access()
	@app_commands.guilds(GUILD)
	async def userinfo(self, interaction: discord.Interaction, user: discord.User) :
		embed = discord.Embed(title=f"{user.name}({user.id})'s info")
		ban_info = BanDbTransactions().get_all_user(user.id)

		guild_data = {
			"Common Servers" : "\n".join([f"{guild.name}({guild.id})" for guild in self.bot.guilds if user in guild.members])[
			                   :1000],
			"Bans"           : len(ban_info),
			"Bot?"           : "Yes" if user.bot else "No",
			"Flags"          : ", ".join([flag[0] for flag in user.public_flags if flag[1] is True]),
			"Created At"     : user.created_at.strftime("%m/%d/%Y"),

		}
		embed.set_image(url=user.avatar)
		for key, value in guild_data.items() :
			embed.add_field(name=key, value=value, inline=False)
		embed.set_footer(
			text=f"This data may only be used for investigations, and may never be used for non-banwatch related actions.")
		await send_message(interaction.channel, embed=embed)

	@app_commands.command(name="banverification", description="[Staff] change the status of a ban's verification")
	@AccessControl().check_access()
	@app_commands.guilds(GUILD)
	async def verifyban(self, interaction: discord.Interaction, ban_id: str, status: bool, provide_proof: bool) :
		ban = BanDbTransactions().get(int(ban_id), override=True)
		if not ban :
			return await send_response(interaction, f"Ban not found.")
		if ban.verified == status :
			return await send_response(interaction, f"This ban already has that status.")
		user = self.bot.get_user(ban.uid)
		if provide_proof :
			evidence_message = f"Please send a message with the evidence you would like to add to {user.name}'s record, this will be added to the ban ID {ban_id} in our support server. \n Type `cancel` to cancel.\n-# By responding to this message you agree to the evidence being stored in our support server."
			evidence = await await_message(interaction, evidence_message)
			channel = self.bot.get_channel(int(os.getenv("APPROVED")))
			await EvidenceController.add_evidence(interaction, evidence, ban_id, channel, user)
			ban = BanDbTransactions().get(int(ban_id))
		if len(ban.proof) < 1 and status is True :
			return await send_response(interaction, f"Evidence is required to approve a ban.")
		BanDbTransactions().update(ban, verified=status)
		await send_response(interaction, f"{ban_id} verified status changed to {status} by {interaction.user.mention}")

	@app_commands.command(name="banvisibility", description="[staff] Change if a ban is hidden or not.")
	@AccessControl().check_access()
	@app_commands.guilds(GUILD)
	async def banvisibility(self, interaction: discord.Interaction, ban_id: str, status: bool) :
		ban = BanDbTransactions().get(int(ban_id), override=True)
		if not ban :
			return await send_response(interaction, f"Ban not found.")
		BanDbTransactions().update(ban, hidden=status)
		await send_response(interaction, f"{ban_id} hidden status changed to {status} by {interaction.user.mention}")


async def setup(bot: commands.Bot) :
	await bot.add_cog(staff(bot))
