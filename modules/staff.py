import os
import typing

import discord
from discord import app_commands
from discord.ext import commands

from classes.access import AccessControl
from classes.autocorrect import autocomplete_appeal, autocomplete_guild
from classes.bans import Bans
from classes.evidence import EvidenceController
from classes.queue import queue
from classes.rpsec import RpSec
from classes.support.discord_tools import await_message, send_message, send_response
from classes.tasks import pending_bans
from data.variables.messages import evidence_message_template
from database.databaseController import BanDbTransactions, ServerDbTransactions

GUILD = int(os.getenv("GUILD"))


class staff(commands.GroupCog, name="staff") :

	def __init__(self, bot: commands.Bot) :
		self.bot = bot



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
	@app_commands.autocomplete(server=autocomplete_guild)
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
			evidence = await await_message(interaction, evidence_message_template.format(user=user.name, ban_id=ban_id))
			channel = self.bot.get_channel(int(os.getenv("APPROVED")))
			await EvidenceController.add_evidence(interaction, evidence, ban_id, user)
			ban = BanDbTransactions().get(int(ban_id))
		if len(ban.proof) < 1 and status is True :
			return await send_response(interaction, f"Evidence is required to approve a ban.")
		BanDbTransactions().update(ban, verified=status)
		await send_response(interaction, f"{ban_id} verified status changed to {status} by {interaction.user.mention}")

	@app_commands.command(name="banvisibility", description="[staff] Change if a ban is hidden or not.")
	@AccessControl().check_access()
	@app_commands.guilds(GUILD)
	async def banvisibility(self, interaction: discord.Interaction, ban_id: str, hide: bool) :
		ban = BanDbTransactions().get(int(ban_id), override=True)
		if not ban :
			return await send_response(interaction, f"Ban not found.")
		BanDbTransactions().update(ban, hidden=hide)
		await send_response(interaction, f"{ban_id} hidden status changed to {hide} by {interaction.user.mention}")

	@app_commands.command(name="rpsecsearch",
	                      description="[DEV] Searches the rp security threads for a specific entry")
	@AccessControl().check_access()
	async def rpseclookup(self, interaction: discord.Interaction, user: discord.User) :
		await send_response(interaction, f"Checking threads", ephemeral=True)
		dev_guild: discord.Guild = self.bot.get_guild(self.bot.SUPPORTGUILD)
		record = dev_guild.get_thread(RpSec.get_user(user.id))
		if record is None :
			await send_response(interaction, "No Roleplay Security Bot entry found")
		await send_response(interaction, f"Roleplay Security Bot entry: {record.mention}")

	@app_commands.command(name="revokeban", description="[DEV] Revokes a ban message. This does not unban the user.")
	@AccessControl().check_access()
	async def revokeban(self, interaction: discord.Interaction, banid: str, reason: str) :
		await interaction.response.send_message("Queueing the search for the embed")
		await Bans().revoke_bans(self.bot, banid, reason, staff=True)
		queue().add(pending_bans(self.bot, True))

	@app_commands.command(name="amistaff", description="[DEV] check if you're a banwatch staff member.")
	async def amistaff(self, interaction: discord.Interaction) :
		return await send_response(interaction, "You are a staff member" if AccessControl().access_all(
			interaction.user.id) else "You are not a staff member")

	@app_commands.command(name="calculate_banid", description="Calculates the ban id with user id and guild id")
	@AccessControl().check_access()
	@app_commands.autocomplete(guild=autocomplete_guild)
	async def calc_banid(self, interaction: discord.Interaction, user: discord.User, guild: str):
		await send_response(interaction, f"The ban_id would be: {user.id + int(guild)}")

async def setup(bot: commands.Bot) :
	await bot.add_cog(staff(bot))
