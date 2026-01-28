import asyncio

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from discord_py_utilities.bans import ban_user, dm_user
from discord_py_utilities.messages import send_message, send_response

from classes.autocorrect import autocomplete_guild
from classes.bans import Bans
from classes.queue import queue
from database.transactions.BanTransactions import BanTransactions
from database.transactions.ServerTransactions import ServerTransactions
from view.modals.inputmodal import send_modal
from view.multiselect.selectreason import SelectReason


class Tools(commands.Cog, description="Moderation tools for managing bans, kicks, and server members."):

	def __init__(self, bot: commands.Bot) :
		self.bot = bot

	@app_commands.command(name="ban", description="Ban a user with an optional reason and notification.")
	@app_commands.checks.has_permissions(ban_members=True)
	@app_commands.choices(ban_type=[
		Choice(name="Normal", value=""),
		Choice(name="Silent", value="[silent]"),
		Choice(name="Hidden", value="[hidden]")
	])
	async def ban(self, interaction: discord.Interaction, user: discord.User, ban_type: Choice[str] = "",
	              inform: bool = True, clean: bool = False) :
		"""
		Bans a specified user from the server. This command offers options for silent bans, message cleaning, and whether to notify the user. A reason for the ban will be requested.

		**Permissions:**
		- Requires `Ban Members` permission.
		"""
		# await interaction.response.defer(ephemeral=True)
		view = SelectReason()
		await send_message(interaction.channel, "Select your reason.", view=view)
		await view.wait()
		reason = view.get_reason()
		if isinstance(ban_type, Choice) :
			ban_type = ban_type.value
		if reason == "custom":
			reason= await send_modal(view.interaction, "What is the reason for the ban?", "Ban Reason")
		await ban_user(interaction, user, ban_type, reason, inform=inform, clean=clean, ban_class=Bans())

	@app_commands.command(name="mass_ban", description="Ban multiple users with an optional reason.")
	@app_commands.checks.has_permissions(ban_members=True)
	@app_commands.choices(ban_type=[
		Choice(name="Normal", value=""),
		Choice(name="Silent", value="[silent]"),
		Choice(name="Hidden", value="[hidden]")
	])
	async def mass_ban(self, interaction: discord.Interaction, users: str, ban_type: Choice[str] = "",
	                   inform: bool = True, clean: bool = False) :
		"""
		Bans multiple users from the server simultaneously. This is an efficient tool for handling raids or removing multiple disruptive users at once. A single reason will apply to all.

		**Permissions:**
		- Requires `Ban Members` permission.
		"""
		view = SelectReason()
		await send_message(interaction.channel, "Select your reason.", view=view)
		await view.wait()
		reason = view.reason

		if isinstance(ban_type, Choice) :
			ban_type = ban_type.value


		if reason == "custom":
			reason= await send_modal(interaction, "What is the reason for the ban?", "Ban Reason")
		user_list = users.split(" ")
		for user_id in user_list :
			await asyncio.sleep(1)
			try :
				user = await self.bot.fetch_user(int(user_id))
			except discord.errors.NotFound :
				await interaction.channel.send(f"User with id {user_id} not found")
				continue
			except :
				await interaction.channel.send(
					f"An error occurred while fetching user with id {user_id}, please ban them manually")
				continue
			await ban_user(interaction, user, ban_type, reason, inform=inform, clean=clean, ban_class=Bans())

	@app_commands.command(name="unban", description="Unban a user from the server.")
	@app_commands.checks.has_permissions(ban_members=True)
	async def unban(self, interaction: discord.Interaction, user: discord.User) :
		"""
		Revokes a ban for a specified user, allowing them to rejoin the server. This is essential for correcting banning mistakes or allowing users to return after an appeal.

		**Permissions:**
		- Requires `Ban Members` permission.
		"""

		try :
			await interaction.guild.unban(user)
		except discord.NotFound :
			return await send_message(interaction.channel, "User is not banned/cannot be found")
		embed = discord.Embed(title=f"{user.name} unbanned", color=discord.Color.green())
		await interaction.channel.send(embed=embed)

	@app_commands.command(name="mass_unban", description="Unban multiple users from the server.")
	@app_commands.checks.has_permissions(ban_members=True)
	async def mass_unban(self, interaction: discord.Interaction, users: str) :
		"""
		Revokes bans for multiple users simultaneously. This is useful for processing multiple successful appeals at once or reversing a mass ban action.

		**Permissions:**
		- Requires `Ban Members` permission.
		"""
		await interaction.response.send_message(f"Unbanning {users}", ephemeral=True)
		user_list = users.split(" ")
		for user_id in user_list :
			await asyncio.sleep(1)
			try :
				user = await self.bot.fetch_user(int(user_id))
			except discord.errors.NotFound :
				await interaction.channel.send(f"User with id {user_id} not found")
				continue
			except Exception :
				await interaction.channel.send(
					f"An error occurred while fetching user with id {user_id}, please unban them manually")
				continue
			try :
				await interaction.guild.unban(user)
			except discord.errors.NotFound :
				await interaction.channel.send(f"user with id {user_id} is not banned")
				continue
			embed = discord.Embed(title=f"{user.name} unbanned", color=discord.Color.green())
			await interaction.channel.send(embed=embed)

	@app_commands.command(name="reban", description="Unban and reban a user to update the reason.")
	@app_commands.checks.has_permissions(ban_members=True)
	@app_commands.choices(ban_type=[
		Choice(name="Normal", value=""),
		Choice(name="Silent", value="[silent]"),
		Choice(name="Hidden", value="[hidden]")
	])
	async def reban(self, interaction: discord.Interaction, user: discord.User, ban_type: Choice[str] = "",
	                reason: str = "Ban being updated using /reban") :
		"""
		Updates a user's ban reason by unbanning and immediately re-banning them with a new reason. This is useful for correcting or updating ban records without requiring the user to be present.

		**Permissions:**
		- Requires `Ban Members` permission.
		"""
		if isinstance(ban_type, Choice) :
			ban_type = ban_type.value
		reason_modal = await send_modal(interaction, "What is the new reason for the ban?", "Ban Reason")
		try :
			await interaction.guild.unban(user, reason=reason)
		except discord.errors.NotFound :
			pass
		await asyncio.sleep(3)
		try :
			await ban_user(interaction, user, ban_type, reason_modal, inform=False, ban_class=Bans())
		except discord.Forbidden :
			await send_response(interaction, "I don't have permission to ban this user")

	@app_commands.command(name="kick", description="Kick a user with an optional reinvite link.")
	@app_commands.checks.has_permissions(kick_members=True)
	async def kick(self, interaction: discord.Interaction, user: discord.User, reinvite: bool = False) :
		"""
		Removes a user from the server. Unlike a ban, a kicked user can rejoin immediately if they have a valid invite. This is a less severe moderation action.

		**Permissions:**
		- Requires `Kick Members` permission.
		"""
		await interaction.guild.kick(user)

		reason_modal = await send_modal(interaction, "What is the reason for the kick?", "Kick Reason")
		reason = reason_modal
		if reinvite :
			invite = await Bans().create_invite(interaction.guild)
			reason = f"{reason}\n\nReinvite link: {invite}"

		await dm_user(interaction, reason, user)
		embed = discord.Embed(title=f"{user.name} kicked", description=reason, color=discord.Color.green())
		await interaction.channel.send(embed=embed)

	@app_commands.command(name="export_bans", description="Export all guild bans to a text file.")
	@app_commands.checks.has_permissions(ban_members=True)
	async def export_bans(self, interaction: discord.Interaction) :
		"""
		Fetches the entire ban list for the server and compiles it into a text file. This is extremely useful for auditing, backup, or migrating bans to another server or bot.

		**Permissions:**
		- Requires `Ban Members` permission.
		"""
		await interaction.response.defer(ephemeral=True)

		# Fetch all bans
		bans = interaction.guild.bans()

		# Write bans to a text file
		with open("bans.txt", "w", encoding='utf-16') as file :
			async for ban_entry in bans :
				user = ban_entry.user
				reason = ban_entry.reason if ban_entry.reason else "No reason provided"
				file.write(f"User: {user} (ID: {user.id}) - Reason: {reason}\n")

		# Send the file to the channel
		await interaction.followup.send("Here are all your bans!", file=discord.File("bans.txt"))

	@app_commands.command(name="search_bans", description="Search bans for specific words.")
	@app_commands.checks.has_permissions(ban_members=True)
	async def search_bans(self, interaction: discord.Interaction, word: str, hide: bool = False) :
		"""
		Searches the server's ban database for entries containing a specific word or phrase in the reason. This helps moderators find patterns or locate specific cases quickly.

		**Permissions:**
		- Requires `Ban Members` permission.
		"""
		await send_response(interaction, f"Checking bans for the word `{word}`")
		bans = ServerTransactions().get_bans(interaction.guild.id)
		with open("bans.txt", "w", encoding='utf-16') as file :
			for ban_entry in bans :
				if word in ban_entry.reason :
					file.write(f"ban id: {ban_entry.uid} - Reason: {ban_entry.reason}\n")
					if hide :
						BanTransactions().update(ban_entry, hidden=True)
		# Send the file to the channel
		await interaction.followup.send(f"Here are all your bans with `{word}`!", file=discord.File("bans.txt"))

	@app_commands.command(name="copy_bans", description="Copy bans from one server to another.")
	@app_commands.checks.has_permissions(ban_members=True)
	@app_commands.autocomplete(guild=autocomplete_guild)
	async def copy_bans(self, interaction: discord.Interaction, guild: str) :
		"""
		Copies all bans from a specified source server to the current server. This is designed for server owners to synchronize ban lists between servers they manage.

		**Permissions:**
		- Requires `Ban Members` permission.
		- User must be the owner of both servers.
		"""
		guild = interaction.client.get_guild(int(guild))
		if interaction.guild.owner_id != guild.owner_id :
			return await send_response(interaction, "You can only copy bans between servers you own.")
		current_bans = [ban.user.id async for ban in interaction.guild.bans(limit=None)]
		bans = [ban async for ban in guild.bans(limit=None) if ban.user.id not in current_bans]
		await send_response(interaction, f"Copying {len(bans)} bans, this may take a while! Expected time: {len(bans) * 1} seconds")
		for ban in bans :
			user = interaction.client.get_user(ban.user.id)
			if user is None :
				await asyncio.sleep(1)
				user = await interaction.client.fetch_user(ban.user.id)

			queue().add(ban_user(interaction, user, ban_type="",
			                   reason=f"[Migrated from {guild.name}]{ban.reason}", inform=False, clean=False,
			                   ban_class=Bans()))

async def setup(bot: commands.Bot) :
	await bot.add_cog(Tools(bot))