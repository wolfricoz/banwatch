import logging
import os
import re

import discord
from discord import Interaction, app_commands
from discord.ext.commands import Bot, GroupCog
from discord_py_utilities.messages import send_message, send_response

from classes.access import AccessControl
from classes.configdata import ConfigData
from classes.queue import queue
from data.config.mappings import premium_toggles
from database.databaseController import ConfigDbTransactions


class Premium(GroupCog) :
	toggles = premium_toggles

	def __init__(self, bot: Bot) :
		self.bot = bot
		self.DELETED_USER_RE = re.compile(r"^deleted_user_[0-9a-f]{11,14}$", re.IGNORECASE)

	async def check_deleted(self, banned_user: discord.User | discord.Member) -> bool :
		if banned_user.bot :
			return False
		if not (banned_user.name == banned_user.global_name or banned_user.global_name is None) :
			return False
		if not self.DELETED_USER_RE.match(banned_user.name) :
			return False
		if banned_user.avatar :
			return False
		if banned_user.banner :
			return False
		return True

	@app_commands.command(name="remove_deleted", description="removes deleted accounts from the ban list and server")
	@AccessControl().check_premium()
	async def command(self, interaction: Interaction) :
		await send_response(interaction, "Checking for deleted accounts...", ephemeral=True)
		deleted_bans = []
		kicked_users = []

		async for ban in interaction.guild.bans() :
			banned_user = ban.user
			if not await self.check_deleted(banned_user) :
				continue
			deleted_bans.append(f"{banned_user.name}({banned_user.id})")
			queue().add(interaction.guild.unban(banned_user, reason="Removing deleted account from ban list"))
			logging.info(f"Removed {banned_user.name} ({banned_user.id})")
		for member in interaction.guild.members :

			if not await self.check_deleted(member) :
				continue
			kicked_users.append(f"{member.global_name}({member.id})")
			logging.info(f"Kicked {member.name} ({member.id})")
			try :
				queue().add(interaction.guild.kick(member, reason="Removing deleted account from server"))
			except discord.Forbidden :
				queue().add(
					send_message(interaction.channel, f"⚠️ I do not have permission to kick {member.name} ({member.id})"))

		with open("deleted_removal.txt", "w") as banlist_file :
			banlist_file.write("Removed the following deleted accounts from bans and kicks:\n\n")
			if deleted_bans :
				banlist_file.write("Banned Accounts Removed:\n")
				for entry in deleted_bans :
					banlist_file.write(f"{entry}\n")
				banlist_file.write("\n")
			if kicked_users :
				banlist_file.write("Kicked Members Removed:\n")
				for entry in kicked_users :
					banlist_file.write(f"{entry}\n")

		await send_message(interaction.channel,
		                   f"Successfully removed deleted {len(deleted_bans) + len(kicked_users)} accounts.",
		                   files=[discord.File(banlist_file.name)]
		                   )
		os.remove(banlist_file.name)

	@app_commands.command(name="toggle_feature", description="Toggles a premium feature on or off")
	@AccessControl().check_premium()
	async def toggle_feature(self, interaction: Interaction, feature_name: str, enable: bool) :
		await send_response(interaction, f"Toggling feature `{feature_name}` to `{'enabled' if enable else 'disabled'}`",
		                    ephemeral=True)
		ConfigDbTransactions.toggle_add(feature_name, enable)

		


async def setup(bot: Bot) :
	await bot.add_cog(
		Premium(bot),
	)
