import logging
import os
import re

import discord
from discord import Interaction, app_commands
from discord.app_commands import Choice
from discord.ext.commands import Bot, GroupCog
from discord_py_utilities.messages import send_message, send_response

from classes.access import AccessControl
from classes.configdata import ConfigData
from classes.queue import queue
from data.config.mappings import premium_toggles
from database.databaseController import ConfigDbTransactions
from view.buttons.bottrap import bottrap


class Premium(GroupCog) :
	toggles = premium_toggles

	def __init__(self, bot: Bot) :
		self.bot = bot
		self.DELETED_USER_RE = re.compile(r"^deleted_user_[0-9a-f]{11,14}$", re.IGNORECASE)
		self.bot.add_view(bottrap())

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
	@app_commands.checks.has_permissions(manage_guild=True)
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


	@app_commands.command(name="bot_trap_button", description="Create a bot trap button in the channel, when pressed will ban the user")
	@app_commands.checks.has_permissions(manage_guild=True)
	@AccessControl().check_premium()
	async def trapbutton(self, interaction: discord.Interaction):
		view = bottrap()
		embed = discord.Embed(title="Get Access (for bots!)", description="Press the buttons below or react to this to be banned from the server!\nKeywords: Gain Access, Verify, rules, accept, agree, click, press\n\n*This is a bot trap, pressing the button will result in an automatic ban from the server.*", color=0xff0000)
		embed.set_footer(text="Bot Trap Button")
		msg = await send_message(interaction.channel, "-# gain access, for bots!",embed=embed, view=view)
		await msg.add_reaction("✅")

	@app_commands.command(name="bot_trap_role", description="Set a role that will automatically be banned when they get it")
	@app_commands.checks.has_permissions(manage_guild=True)
	@AccessControl().check_premium()
	async def traprole(self, interaction: discord.Interaction, role: discord.Role):
		ConfigDbTransactions.config_unique_add(interaction.guild.id, "TRAP_ROLE", role.id)
		await send_response(interaction, f"Set the bot trap role to {role.mention}", ephemeral=True)

	@app_commands.command(name="toggle_feature", description="Toggles a premium feature on or off")
	@app_commands.choices(feature_name=[
		app_commands.Choice(name=feature, value=feature) for feature in toggles.keys()
	])
	@AccessControl().check_premium()
	async def toggle_feature(self, interaction: Interaction, feature_name: Choice[str], enable: bool) :
		await send_response(interaction, f"Toggling feature `{feature_name.value}` to `{'enabled' if enable else 'disabled'}`",
		                    ephemeral=True)
		ConfigDbTransactions.toggle_add(interaction.guild.id, feature_name.value, enable)

		


async def setup(bot: Bot) :
	await bot.add_cog(
		Premium(bot),
	)
