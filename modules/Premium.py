import asyncio
import logging
import os
import re
import tempfile

import discord
from discord import Interaction, app_commands
from discord.app_commands import Choice
from discord.ext.commands import Bot, GroupCog
from discord_py_utilities.bans import ban_user
from discord_py_utilities.messages import send_message, send_response

from classes.access import AccessControl
from classes.autocorrect import autocomplete_guild
from classes.bans import Bans
from classes.queue import queue
from data.config.mappings import premium_toggles
from database.transactions.BanReasonTransactions import BanReasonsTransactions
from database.transactions.BanTransactions import BanTransactions
from database.transactions.ConfigTransactions import ConfigTransactions
from database.transactions.ServerTransactions import ServerTransactions
from view.buttons.bottrap import bottrap
from view.modals.banreasonmodal import send_banreason_modal


class Premium(GroupCog, name="premium") :
	"""
	Exclusive commands for servers with a premium subscription.
	"""
	toggles = premium_toggles

	def __init__(self, bot: Bot) :
		self.bot = bot
		self.DELETED_USER_RE = re.compile(r"^deleted_user_[0-9a-f]{11,14}$", re.IGNORECASE)
		self.bot.add_view(bottrap())

	async def check_deleted(self, banned_user: discord.User | discord.Member) -> bool :
		"""[skip]"""
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

	@app_commands.command(name="remove_deleted", description="[PREMIUM] Removes deleted user accounts from your server and ban list.")
	@app_commands.checks.has_permissions(manage_guild=True)
	@AccessControl().check_premium()
	async def remove_deleted(self, interaction: Interaction) :
		"""
		Scans the server's ban list and removes entries for deleted user accounts, and kicks any deleted accounts still present in the server! This will help you clean up IP bans and ensure your server is free of inactive or deleted users.

		Why would you want to remove IP bans for deleted users? In many cases the IP has been reassigned to a new person because most ISPs recycle IP addresses. Keeping bans for deleted users can inadvertently block new users who are assigned those IPs, potentially causing frustration and loss of legitimate members.

		**Permissions:**
		- `Manage Server`
		- `Premium Server`
		"""
		await send_response(interaction, "Removing deleted users from ban list...", ephemeral=True)
		banlist = [entry async for entry in interaction.guild.bans(limit=None)]
		banlist_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
		deleted_bans = []
		kicked_users = []

		for ban in banlist :
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


	@app_commands.command(name="bot_trap_button", description="[PREMIUM] Creates a button that bans any user who clicks it.")
	@app_commands.checks.has_permissions(manage_guild=True)
	@AccessControl().check_premium()
	async def trapbutton(self, interaction: discord.Interaction):
		"""
		Creates a message with a button that instantly bans any user who clicks it.
		Useful for catching malicious bots. Make sure to warn your members not to click it!

		This feature is currently a test; if you have feedback on how to improve its efficacy, please reach out to the support server.

		**Permissions:**
		- `Manage Server`
		- `Premium Server`
		"""
		view = bottrap()
		await send_response(interaction, "Creating bot trap button...", ephemeral=True)
		embed = discord.Embed(title="Bot Trap", description="This button is a trap for bots. Do not click it.",
		                      color=0xff0000)
		embed.set_footer(text="Bot Trap Button")
		msg = await send_message(interaction.channel, "-# gain access, for bots!",embed=embed, view=view)
		await msg.add_reaction("✅")

	@app_commands.command(name="bot_trap_role", description="[PREMIUM] Designates a role that will ban a user upon receiving it.")
	@app_commands.checks.has_permissions(manage_guild=True)
	@AccessControl().check_premium()
	async def traprole(self, interaction: discord.Interaction, role: discord.Role):
		"""
		[PREMIUM] Designates a 'trap role'. Any user assigned this role will be instantly banned. This is useful for catching bots that assign themselves roles through onboarding or other automated processes; simply assign the trap role to the bot and it will be banned when the task runs (every hour!).

		This feature is currently a test; if you have feedback on how to improve its efficacy, please reach out to the support server.

		**Permissions:**
		- `Manage Server`
		- `Premium Server`
		"""
		ConfigTransactions().config_unique_add(interaction.guild.id, "TRAP_ROLE", role.id)
		await send_response(interaction, f"Set the bot trap role to {role.mention}", ephemeral=True)

	@app_commands.command(name="toggle_feature", description="[PREMIUM] Toggles a specific premium feature on or off for your server.")
	@app_commands.choices(feature_name=[
		app_commands.Choice(name=feature, value=feature) for feature in toggles.keys()
	])
	@AccessControl().check_premium()
	async def toggle_feature(self, interaction: discord.Interaction, feature_name: app_commands.Choice[str], enable: bool) :
		"""
		Toggles various premium features on or off for the server. Choose the feature you want to enable or disable from the list.

		**Permissions:**
		- `Manage Server`
		- `Premium Server`
		"""
		await send_response(interaction, f"Toggling feature `{feature_name.value}` to `{'enabled' if enable else 'disabled'}`",
		                    ephemeral=True)
		ConfigTransactions().toggle_add(interaction.guild.id, feature_name.value, enable)



	@app_commands.command(name="ban_presets", description="[PREMIUM] Manage preset ban reasons for quick and consistent moderation.")
	@app_commands.checks.has_permissions(manage_guild=True)
	@app_commands.choices(operation=[
		Choice(name="list", value="list"),
		Choice(name="add", value="add"),
		Choice(name="remove", value="remove")
	])
	@AccessControl().check_premium()
	async def ban_presets(self, interaction: discord.Interaction, operation: Choice[str], name: str = None) :
		"""
		Manages preset ban reasons for quick moderation. They will appear on the top of the ban reason list when banning a user with the ban command.
		Allows adding, removing, and listing presets.

		**Permissions:**
		- `Manage Server`
		- `Premium Server`
		"""
		if operation.value == "list" :
			presets = ConfigTransactions().config_key_get(interaction.guild.id, "BAN_PRESET")
			if not presets :
				return await send_response(interaction, "No ban presets found.", ephemeral=True)
			preset_list = "\n".join([f"- {preset}" for preset in presets.split(",")])
			await send_response(interaction, f"Current Ban Presets:\n{preset_list}", ephemeral=True)
		elif operation.value == "add" :
			if not name :
				return await send_response(interaction, "Please provide a name for the ban preset.", ephemeral=True)
			existing = ConfigTransactions().config_key_get(interaction.guild.id, "BAN_PRESET", key_value=name)
			if existing :
				return await send_response(interaction, f"Ban preset `{name}` already exists.", ephemeral=True)
			ConfigTransactions().config_unique_add(interaction.guild.id, "BAN_PRESET", name)
			await send_response(interaction, f"Added ban preset `{name}`.", ephemeral=True)
		elif operation.value == "remove" :
			if not name :
				return await send_response(interaction, "Please provide the name of the ban preset to remove.", ephemeral=True)
			existing = ConfigTransactions().config_key_get(interaction.guild.id, "BAN_PRESET", key_value=name)
			if not existing :
				return await send_response(interaction, f"Ban preset `{name}` does not exist.", ephemeral=True)
			ConfigTransactions().config_unique_remove(interaction.guild.id, "BAN_PRESET", name)
			await send_response(interaction, f"Removed ban preset `{name}`.", ephemeral=True)

	@app_commands.command(name="search_bans", description="Search bans for specific words.")
	@app_commands.checks.has_permissions(ban_members=True)
	@AccessControl().check_premium()
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
	@AccessControl().check_premium()
	async def copy_bans(self, interaction: discord.Interaction, guild: str) :
		"""
		Copies all bans from a specified source server to the current server. This is designed for server owners to synchronize ban lists between servers they manage.

		**Permissions:**
		- Requires `Ban Members` permission.
		- User must be the owner of both servers.
		- Premium feature.
		"""

		guild = interaction.client.get_guild(int(guild))
		if interaction.guild.owner_id != guild.owner_id :
			return await send_response(interaction, "You can only copy bans between servers you own.")
		current_bans = [ban.user.id async for ban in interaction.guild.bans(limit=None)]
		bans = [ban async for ban in guild.bans(limit=None) if ban.user.id not in current_bans]
		await send_response(interaction,
		                    f"Copying {len(bans)} bans, this may take a while! Expected time: {len(bans) * 1} seconds")
		for ban in bans :
			user = interaction.client.get_user(ban.user.id)
			if user is None :
				await asyncio.sleep(1)
				user = await interaction.client.fetch_user(ban.user.id)

			queue().add(ban_user(interaction, user, ban_type="",
			                     reason_modal=f"[Migrated from {guild.name}]{ban.reason}", inform=False, clean=False,
			                     ban_class=Bans()))


async def setup(bot: Bot) :
	await bot.add_cog(
		Premium(bot),
	)
