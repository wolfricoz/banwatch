import logging
import os
import time
from abc import ABC

import discord
from discord import app_commands
from discord.ext import commands
from discord_py_utilities.messages import send_message, send_response

from classes.access import AccessControl
from database.transactions.BanTransactions import BanDbTransactions
from view.buttons.lookup import LookUp


class BanCheck(ABC) :

	def member_count_check(self, guild, bot) :
		if guild.id == bot.SUPPORTGUILD :
			return
		return len(guild.members) >= 50

	async def checkerall(self, interaction, bot) :
		bcount = 0
		cache = BanDbTransactions().local_cache
		with open(f"bans.txt", 'w', encoding='utf-8') as f :
			f.write(f"Bans:")
		for member in interaction.guild.members :
			if str(member.id) not in cache :
				continue
			with open(f"bans.txt", 'a', encoding='utf-8') as f :
				f.write(f"\n----{member}({member.id})----:")
			for ban in cache[str(member.id)] :
				info = cache[str(member.id)][str(ban)]
				bcount += 1
				with open(f"bans.txt", 'a', encoding='utf-8') as f :
					f.write(f"\n\nGuild: {info['guild']}"
					        f"\nReason: {info['reason']}"
					        f"\nDate: {info['date']}"
					        f"\nverified: {info['verified']}")
		with open(f"bans.txt", encoding='utf-8') as f :
			await send_message(interaction.channel, f"Bans found :",
			                   files=[discord.File(f.name, "banned.txt")], error_mode='warn')
		os.remove(f.name)
		return bcount


class User(commands.GroupCog, name="user") :

	def __init__(self, bot: commands.Bot) :
		self.bot = bot

	@app_commands.command(name="lookup", description="Looks up user's bans and displays them in the channel")
	@app_commands.checks.has_permissions(ban_members=True)  # Ensure the user has the 'ban_members' permission
	async def lookup(self, interaction: discord.Interaction, user: discord.User = None, ban_id: str = None,
	                 override: bool = False) :

		# Check if override is enabled and the user has access to use it
		if override and not AccessControl().check_access() :
			logging.warning(f"Access denied for override by {interaction.user}.")
			return await send_response(interaction, "Only Banwatch staff may use the override toggle.")

		# Ensure at least one of 'ban_id' or 'user' is provided
		if ban_id is None and user is None :
			logging.info("Neither ban_id nor user provided.")
			return await send_response(interaction, "You need to provide a user or ban id to look up.", ephemeral=True)

		# Handle lookup by ban ID
		if ban_id :
			ban = BanDbTransactions().get(int(ban_id), override=override)  # Fetch ban details by ID
			if ban is None :  # If no ban is found, notify the user
				logging.warning(f"Ban with id {ban_id} not found.")
				return await send_response(interaction, "Ban not found.")
			user = await self.bot.fetch_user(ban.uid)  # Fetch the user associated with the ban
			logging.info(f"Fetched user {user} for ban_id {ban_id}.")
			await send_response(interaction, "⌛ Fetching bans, please wait.", ephemeral=True)  # Notify the user
			view: LookUp = LookUp(user_id=user.id)  # Create a view for displaying the ban details
			logging.info(f"Sending ban details for user {user.id}.")
			await view.send_message(interaction.client, interaction.channel, [ban], user,
			                        override=override)  # Send the ban details
			return

		# Prevent users from looking up their own bans (except in the support guild)
		if interaction.user.id == user.id and not interaction.guild.id == self.bot.SUPPORTGUILD :
			logging.warning(f"{interaction.user} tried to look up themselves.")
			return await send_response(interaction, "You can not look up yourself!", ephemeral=True)

		# Fetch all bans for the specified user
		sr = BanDbTransactions().get_all_user(user_id=user.id, override=override)
		if sr is None :  # If no bans are found, notify the user
			logging.info(f"No bans found for user {user.id}.")
			await send_response(interaction, f"<@{user.id}> is not banned in any servers the bot is in.")
			return

		# Notify the user that bans are being fetched
		await send_response(interaction, "⌛ Fetching bans, please wait.", ephemeral=True)

		# Create a view for displaying the bans and send the details
		view: LookUp = LookUp(user_id=user.id)
		logging.info(f"Sending ban details for user {user.id}.")
		await view.send_message(interaction.client, interaction.channel, sr, user, interaction=interaction,
		                        override=override)

	@app_commands.command(name="checkall", description="checks ALL users")
	@app_commands.checks.has_permissions(ban_members=True)
	async def checkall(self, interaction: discord.Interaction) :
		await send_response(interaction,
		                    f"Checking all users ({len(interaction.guild.members)}), please wait. Looking through {BanDbTransactions().count()} unique bans")
		start = time.time()
		count = 0
		logging.info("Starting checkall")
		count += await BanCheck().checkerall(interaction, self.bot)
		logging.info(f"Checkall done, found {count} bans.")
		end = time.time()
		total = end - start
		logging.info(f"Checkall took {total} seconds.")
		await send_message(interaction.channel,
		                   f"Check-up done, found {count} ban registries in {str(total)[0 :4]} seconds."
		                   f"\n-# Reminder: You should reach out to the owner of the server for more information on the ban. Some of these bans may be older than the bot and have not been verified.", error_mode='warn')


async def setup(bot: commands.Bot) :
	await bot.add_cog(User(bot))
