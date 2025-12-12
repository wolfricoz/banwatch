import logging

import discord
from discord.ext.commands import Cog, GroupCog, Bot

from classes.access import AccessControl
from classes.configdata import ConfigData


class on_member_update(Cog) :

	def __init__(self, bot: Bot) :
		self.bot = bot

	@Cog.listener()
	async def on_member_update(self, before: discord.Member, after: discord.Member) :
		"""Checks if the trap role was added to a member"""
		# Setting up variables
		guild = after.guild
		if not AccessControl().is_premium(guild.id) :
			return
		added_roles = set(after.roles) - set(before.roles)
		if not added_roles :
			return

		purge_role = int(ConfigData().get_key(guild.id, "trap_role", 0))
		if purge_role == 0 :
			return
		if added_roles :
			# A role was added. 'after' is the member object.
			for role in added_roles :
				if role.id == purge_role:
					try:
						await guild.ban(after, reason="Trap role detected - automatic ban", delete_message_days=0)
					except Exception as e:
						logging.info(f"Failed to ban member {after.id} in guild {guild.id} for trap role: {e}", exc_info=True)
					break


async def setup(bot: Bot) :
	await bot.add_cog(
		on_member_update(bot),
	)
