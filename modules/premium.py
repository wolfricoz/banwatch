import logging
import re


import discord
from discord import Interaction, app_commands
from discord.ext.commands import GroupCog, Bot
from discord_py_utilities.messages import send_message, send_response

from classes.access import AccessControl
from classes.queue import queue


class Premium(GroupCog) :

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
	# @AccessControl().check_premium()
	async def command(self, interaction: Interaction) :
		await send_response(interaction, "Checking for deleted accounts...", ephemeral=True)
		deleted_bans = 0
		kicked_users = 0

		async for ban in interaction.guild.bans() :
			banned_user = ban.user
			if not await self.check_deleted(banned_user) :
				continue
			deleted_bans += 1
			await interaction.guild.unban(banned_user, reason="Removing deleted account from ban list")
			logging.info(f"Removed {banned_user.name} ({banned_user.id})")
		for member in interaction.guild.members :

			if not await self.check_deleted(member) :
				continue
			kicked_users += 1
			logging.info(f"Kicked {member.name} ({member.id})")
			try:
				await interaction.guild.kick(member, reason="Removing deleted account from server")
			except discord.Forbidden :
				queue().add(send_message(interaction.channel, f"⚠️ I do not have permission to kick {member.name} ({member.id})"))

		await send_response(interaction, f"Successfully removed deleted {deleted_bans + kicked_users} accounts.", ephemeral=True)



			# if banned_user.bot:
			# 	continue
			# if banned_user.global_name ==  :
			# 	deleted_bans += 1
			# 	await interaction.guild.unban(banned_user, reason="Removing deleted account from ban list")
			# member = interaction.guild.get_member(banned_user.id)
			# if member is not None and member.deleted :
			# 	kicked_users += 1
			# 	await interaction.guild.kick(member, reason="Removing deleted account from server")



async def setup(bot: Bot) :
	await bot.add_cog(
		Premium(bot),
	)
