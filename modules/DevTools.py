import asyncio
from datetime import datetime
from typing import Coroutine

import discord
import os
import re
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
import logging

from discord_py_utilities.messages import send_message, send_response

from classes.access import AccessControl
from classes.bans import Bans
from classes.configdata import ConfigData
from classes.configer import Configer
from classes.evidence import EvidenceController
from classes.queue import queue
from classes.tasks import pending_bans
from database.transactions.BanMessageTransactions import BanMessageTransactions
from database.transactions.FlaggedTermsTransactions import FlaggedTermsTransactions

from database.transactions.StaffTransactions import StaffTransactions
from database.transactions.BanTransactions import BanTransactions
from database.transactions.ServerTransactions import ServerTransactions
from database.transactions.BanReasonTransactions import DatabaseTransactions
from view.modals.inputmodal import send_modal
from discord.utils import get

OWNER = int(os.getenv("OWNER"))
GUILD = int(os.getenv("GUILD"))

SUPPORT_GUILD = discord.Object(GUILD)


class DevTools(commands.GroupCog, name="dev") :
	"""
	Developer-only commands for bot maintenance, administration, and debugging.
	"""

	def __init__(self, bot: commands.Bot) :
		self.bot = bot

	async def inform_server(self, guild, banembed) :
		config = ConfigData().get_key(guild.id, "modchannel")
		modchannel = self.bot.get_channel(int(config))
		await modchannel.send(embed=banembed)

	@app_commands.command(name="updatecommands", description="[DEV] Syncs all application commands globally.")
	@AccessControl().check_access("DevTools")
	async def update_commands(self, interaction: discord.Interaction) :
		"""
		[DEV] Unloads and syncs all application commands globally.

		**Permissions:**
		- `Developer`
		"""
		queue().add(self.bot.tree.sync(), priority=2)
		for cog in self.bot.cogs :
			try :
				self.bot.remove_cog(cog.qualified_name)
			except Exception as e :
				logging.warning(f"Failed to unload cog {cog.qualified_name}: {e}")
		await send_response(interaction,"Command sync queue, high priority queue.")

	@app_commands.command(name="stats", description="[DEV] View Banwatch's operational statistics.")
	async def stats(self, interaction: discord.Interaction) :
		"""
		[DEV] Displays operational statistics for the bot.

		**Permissions:**
		- `Developer`
		"""
		with open('countbans.txt', 'w') :
			pass
		await Bans().update(self.bot, override=True)
		stats = {
			"servers_total" : ServerTransactions().count(),
			"bans_total"    : BanTransactions().count(),
			"verified_bans" : BanTransactions().count(result_type="verified"),
			"deleted_bans"  : BanTransactions().count(result_type="deleted"),
			"hidden_bans"   : BanTransactions().count(result_type="hidden"),
			"available"     : BanTransactions().count(result_type="available"),
			"queue-status"  : queue().status()
		}
		embed = discord.Embed(title="Banwatch's stats")
		for i, v in stats.items() :
			embed.add_field(name=i, value=v, inline=False)
		await send_response(interaction, "Here are the stats!", embed=embed, ephemeral=True)

	@app_commands.command(name="loadflaggedterms", description="[DEV] Loads the old watchlist config into the new flagged terms table.")
	@AccessControl().check_access("DevTools")
	async def update_flagged_terms(self, interaction: discord.Interaction) :
		"""
		[DEV] Migrates flagged terms from the old config to the new database table.

		**Permissions:**
		- `Developer`
		"""
		checklist = await Configer.get_checklist()
		for word in checklist :
			try:
				FlaggedTermsTransactions().add(term=word, action='review')
			except Exception as e:
				logging.warning(f"could not load {word} into flagged terms: {e}")

		await send_response(interaction,f"Old watchlist flagged terms have been successfully loaded. loaded: ||{', '.join(checklist)}||")


	@app_commands.command(name="announce", description="[DEV] Sends an announcement to the mod channel of all servers.")
	@AccessControl().check_access("DevTools")
	async def announce(self, interaction: discord.Interaction) :
		"""
		[DEV] Sends an announcement to the designated mod channel of every server the bot is in.

		**Permissions:**
		- `Developer`
		"""
		message = await send_modal(interaction, "What is the announcement?", "Announcement", 1700)
		if message is None :
			return
		bot = self.bot
		supportguild = bot.get_guild(bot.SUPPORTGUILD)
		support_invite = await Bans().create_invite(supportguild)
		announcement = (f"## BAN WATCH ANNOUNCEMENT"
		                f"\n{message}"
		                f"\n-# You can join our support server by [clicking here to join]({support_invite}). If you have any questions, errors or concerns, please open a ticket in the support server.")

		for guild in self.bot.guilds :
			await asyncio.sleep(1)
			try :
				config = ConfigData().get_key(guild.id, "modchannel")
				configid = int(config)
				channel = self.bot.get_channel(configid)
				await channel.send(announcement)
			except Exception as e :
				try :
					await guild.owner.send(
						f"Banwatch could not send the announcement to your modchannel in {guild.name}, please check the mod channel settings. You can setup your modchannel with: ```/Config change option:Mod channel channel:```")
					await guild.owner.send(announcement)
				except Exception as e :
					await interaction.channel.send(f"Error sending to {guild}({guild.owner}): {e}")

	@app_commands.command(name="leave_server", description="[DEV] Forces the bot to leave a specified server.")
	@AccessControl().check_access("DevTools")
	async def leave_server(self, interaction: discord.Interaction, guildid: int) :
		"""
		[DEV] Makes the bot leave a server specified by its ID.

		**Permissions:**
		- `Developer`
		"""
		guild = self.bot.get_guild(guildid)
		if guild is None :
			return await send_response(interaction, "Guild not found")
		await guild.leave()
		await send_response(interaction,f"Left {guild}")

	@app_commands.command(name="blacklist_server", description="[DEV] Adds a server to the blacklist and leaves it.")
	@AccessControl().check_access("DevTools")
	async def blacklist_server(self, interaction: discord.Interaction, guildid: str) :
		"""
		[DEV] Adds a server to the blacklist, preventing future joins, and leaves it.

		**Permissions:**
		- `Developer`
		"""
		guildid = int(guildid)
		guild = self.bot.get_guild(guildid)
		await Configer.add_to_blacklist(guildid)
		await guild.leave()
		await send_response(interaction,f"Blacklisted {guild}")

	@app_commands.command(name="unblacklist_server", description="[DEV] Removes a server from the blacklist.")
	@AccessControl().check_access("DevTools")
	async def unblacklist_server(self, interaction: discord.Interaction, guildid: str) :
		"""
		[DEV] Removes a server from the blacklist.

		**Permissions:**
		- `Developer`
		"""
		guildid = int(guildid)
		await Configer.remove_from_blacklist(guildid)
		await send_response(interaction,f"Unblacklisted {guildid}")

	# blacklist user goes here
	@app_commands.command(name="blacklist_user", description="[DEV] Adds a user to the blacklist, blocking bot interaction.")
	@AccessControl().check_access("DevTools")
	async def blacklist_user(self, interaction: discord.Interaction, userid: str) :
		"""
		[DEV] Adds a user to the global blacklist, blocking all interactions with the bot.

		**Permissions:**
		- `Developer`
		"""
		userid = int(userid)
		await Configer.add_to_user_blacklist(userid)
		await send_response(interaction, f"Blacklisted {userid}")

	@app_commands.command(name="unblacklist_user", description="[DEV] Removes a user from the blacklist.")
	@AccessControl().check_access("DevTools")
	async def unblacklist_user(self, interaction: discord.Interaction, userid: str) :
		"""
		[DEV] Removes a user from the global blacklist.

		**Permissions:**
		- `Developer`
		"""
		userid = int(userid)
		await Configer.remove_from_user_blacklist(userid)
		await send_response(interaction, f"Unblacklisted {userid}")

	@app_commands.command(name="checklist",
	                      description="[DEV] Manage flagged terms for content moderation.")
	@app_commands.choices(operation=[
		Choice(name="add", value="add"),
		Choice(name="remove", value="remove"),
		Choice(name="list", value="list")
	])
	@AccessControl().check_access("DevTools")
	async def checklist(self, interaction: discord.Interaction, operation: Choice[str], word: str = None) :
		"""
		[DEV] Manages the list of flagged terms for controversial content.

		**Permissions:**
		- `Developer`
		"""
		if operation.value == "add" :
			if word is None :
				return await send_response(interaction, "Please provide a word to add")
			result = FlaggedTermsTransactions().add(term=word, action='review')
			if not result :
				return await send_response(interaction, f"Failed to add {word} to the checklist")
			return await send_response(interaction,f"Added {word} to the flagged terms list", ephemeral=True)

		if operation.value == "remove" :
			if word is None :
				return await send_response(interaction, "Please provide a word to remove")
			result = FlaggedTermsTransactions().delete(word)
			if not result :
				return await send_response(interaction, f"Failed to remove {word} from the checklist")
			return await send_response(interaction,f"Removed {word} from the checklist", ephemeral=True)

		if operation.value == "list" :
			await send_response(interaction, "Fetching flagged words", )
			flaggedWords = FlaggedTermsTransactions().get_all()
			result = ""
			for word in flaggedWords :
				result += f"Term: {word.term} Action: {word.action} Regex: {word.regex}\n"


			with open('flaggedwords.txt', 'w') as file:
				file.write("All flagged words:\n")
				file.write(result)

			return await send_message(interaction.channel, "Here is a list of all flagged words:", files=[discord.File(file.name)])
		return None

	@app_commands.command(name="backup", description="[DEV] Backs up ban and evidence channels to the backup server.")
	@AccessControl().check_access("DevTools")
	async def copy(self, interaction: discord.Interaction, evidence_only: bool = False) :
		"""
		[DEV] Backs up ban and evidence channels to a private backup server.

		**Permissions:**
		- `Developer`
		"""
		await send_response(interaction, "Backup Started", ephemeral=True)
		backup_server = self.bot.get_guild(int(os.getenv("BACKUP_SERVER")))
		if not evidence_only :
			ban_channel = self.bot.get_channel(int(os.getenv("APPROVED")))
			evidence_channel = self.bot.get_channel(int(os.getenv("EVIDENCE")))
			backupsection = get(backup_server.categories, name="backup")
			if backupsection is None :
				backupsection = await backup_server.create_category_channel("backup",
				                                                           overwrites={
					                                                           backup_server.default_role : discord.PermissionOverwrite(
						                                                           read_messages=False)})

			pending_removal: list[Coroutine] = [channel.delete() for channel in backupsection.channels]

			# Instead of static channels, we will now make channels when the bot is ran.

			backupevidence = await backup_server.create_text_channel(f"evidence-{datetime.now().strftime('%m-%d-%Y')}",
			                                                        category=backupsection)
			ban_history = ban_channel.history(limit=None, oldest_first=True)
			evidence_history = evidence_channel.history(limit=None, oldest_first=True)
			bans = BanTransactions().get_all(override=True)
			async for message in evidence_history :
				if message.content.startswith("Evidence") is False :
					continue
				queue().add(
					backupevidence.send(message.content, files=[await attachment.to_file() for attachment in message.attachments],
					                    embeds=message.embeds), 0)
			for channel in pending_removal :
				await channel
			if evidence_only is True :
				return
			backupbans = await backup_server.create_text_channel(f"bans-{datetime.now().strftime('%m-%d-%Y')}",
			                                                    category=backupsection)
			async for message in ban_history :
				if len(message.embeds) < 1 :
					continue
				queue().add(
					backupbans.send(f"{message.content}",
					                files=[await attachment.to_file() for attachment in message.attachments],
					                embeds=message.embeds), 0)

	@app_commands.command(name="rebuild_evidence", description="[DEV] Rebuilds the evidence database from a channel's history.")
	@AccessControl().check_access("DevTools")
	async def rebuild_evidence(self, interaction: discord.Interaction, channel: discord.TextChannel, log: bool = False) :
		"""
		[DEV] Rebuilds the evidence database by scanning messages in a given channel.

		**Permissions:**
		- `Developer`
		"""
		await send_response(interaction, "Rebuilding evidence channel", ephemeral=True)
		async for message in channel.history(limit=None, oldest_first=True) :
			if len(message.embeds) == 0 :
				continue
			try :
				id = int(message.content.replace(":", "").split(" ")[2])
			except :
				logging.warning(f"Failed to extract id from {message.content}")
				continue
			ban = BanTransactions().get(id, override=True)
			if ban is None :
				continue
			try :
				match = re.search(r"```(.*?)```", message.content, flags=re.DOTALL).group(1)
				message.content = match
			except :
				logging.warning(f"Failed to extract message content from {message.content}")
				message.content = ""

			queue().add(EvidenceController.create_evidence_entry(ban.ban_id, message, interaction, int(ban.uid), log_evidence=log), priority=0)
		queue().add(send_message(interaction.channel, "Rebuilding evidence complete"), priority=0)

	@app_commands.command(name="rebuild_bans", description="[DEV] Rebuilds ban database entries from channel history.")
	@AccessControl().check_access("DevTools")
	async def rebuild_bans(self, interaction: discord.Interaction, channel: discord.TextChannel = None, only_messages: bool = False) :
		"""
		[DEV] Rebuilds the bans database by scanning messages in a channel or all server audit logs.

		**Permissions:**
		- `Developer`
		"""
		if channel is None :
			channel = self.bot.get_channel(int(os.getenv("BANWATCH_LOG")))
		await send_response(interaction, f"Rebuilding bans channel", ephemeral=True)
		if only_messages is False :
			await self.find_ban_id(channel)
		logging.info("Rebuilding ban messages from all guilds")
		async def inspect_guild_messages():
			modchannel = await ConfigData().get_channel(guild, "modchannel")
			if modchannel is None :
				return
			async for message in modchannel.history(limit=None, oldest_first=True) :
				# We search for ANY embed with a ban ID in the footer, and then add it to the BanMessages if it's missing
				if len(message.embeds) < 1 :
					return
				embed = message.embeds[0]
				try :
					match = re.search(r'ban ID: (\d+)', embed.footer.text)
				except :
					match = None
				if not match :
					return
				ban_id = int(match.group(1))
				ban = BanTransactions().get(ban_id, override=True)
				if ban is None :
					logging.warning(
						f"[rebuild ban] Ban ID {ban_id} not found in database, deleting message {message.id} in guild {guild.name}")
					queue().add(message.delete(), 0)
					return
				logging.info(f"[rebuild ban] Adding ban message {message.id} for ban ID {ban_id} in guild {guild.name}")
				BanMessageTransactions().add_ban_message(ban_id, guild.id, message.id)

		for guild in self.bot.guilds:
			queue().add(inspect_guild_messages(), 0)





		await interaction.followup.send(f"Rebuilding bans channel complete", ephemeral=True)



	@app_commands.command(name="testban", description="[DEV] Unbans and re-bans the test account in the current server.")
	@AccessControl().check_access("DevTools")
	async def testban(self, interaction: discord.Interaction, checklist: bool = True) :
		"""
		[DEV] Unbans and re-bans the test account for testing purposes.

		**Permissions:**
		- `Developer`
		"""
		user = self.bot.get_user(474365489670389771)
		try :
			await interaction.guild.unban(user)
		except Exception as e :
			await send_message(interaction.channel, f"Failed to unban test account with reason: {e}")
			pass
		try :
			await interaction.guild.ban(user,
			                            reason=f"{'Test Ban that is longer than four words' if checklist else 'DevTools ban that is longer than four words'}")
		except AttributeError :
			user = await self.bot.fetch_user(474365489670389771)
			await interaction.guild.ban(user,
			                            reason=f"{'Test Ban that is longer than four words' if checklist else 'DevTools ban that is longer than four words'}")
		await send_response(interaction,"Test ban complete", ephemeral=True)

	@app_commands.command(name="pendingbans", description="[DEV] Manually triggers a check for all pending bans.")
	@AccessControl().check_access("DevTools")
	async def pendingbans(self, interaction: discord.Interaction) :
		"""
		[DEV] Manually triggers the background task to check for pending bans.

		**Permissions:**
		- `Developer`
		"""
		await pending_bans(self.bot)
		await send_response(interaction, "Checking for pending bans", ephemeral=True)

	@app_commands.command(name="refreshbans", description="[DEV] Manually triggers a refresh of all bans from all servers.")
	@AccessControl().check_access("DevTools")
	async def refreshbans(self, interaction: discord.Interaction) :
		"""
		[DEV] Manually triggers a refresh of all bans from all connected servers.

		**Permissions:**
		- `Developer`
		"""
		await Bans().update(self.bot, override=True)
		await send_response(interaction,"Bans refresh queued", ephemeral=True)

	@app_commands.command(name="add_staff", description="[DEV] Adds a user to the Banwatch staff team.")
	@app_commands.choices(role=[Choice(name=x, value=x.lower()) for x in ["Dev", "Rep"]])
	async def add_staff(self, interaction: discord.Interaction, user: discord.User, role: Choice[str]) :
		"""
		[DEV] Adds a user to the Banwatch staff with a specified role.

		**Permissions:**
		- `Bot Owner`
		"""
		if interaction.user.id != int(os.getenv("OWNER")) :
			return await send_response(interaction, "You do not have permission to add staff members")
		StaffTransactions().add(user.id, role.value)
		await send_response(interaction, f"Staff member {user.mention} successfully added as a `{role.name}`!")
		AccessControl().reload()

	@app_commands.command(name="stop", description="[DEV] Shuts down the bot. Only the bot owner can use this.")
	async def quit(self, interaction: discord.Interaction) :
		"""
		[DEV] Shuts down the bot.

		**Permissions:**
		- `Bot Owner`
		"""
		if interaction.user.id != int(os.getenv("OWNER")) :
			return await send_response(interaction, "You do not have permission to add staff members")
		await send_response(interaction, "Shutting down", ephemeral=True)
		await self.bot.close()
		quit(0)

	@app_commands.command(name="remove_staff", description="[DEV] Removes a staff member from the Banwatch team.")
	@AccessControl().check_access("DevTools")
	async def remove_staff(self, interaction: discord.Interaction, user: discord.User) :
		"""
		[DEV] Removes a user from the Banwatch staff.

		**Permissions:**
		- `Developer`
		"""
		StaffTransactions().delete(user.id)
		await send_response(interaction, f"Staff member {user.mention} successfully removed!")
		AccessControl().reload()

	@app_commands.command(name="test_config", description="[DEV] Tests if the configuration and channel retrieval are working.")
	@AccessControl().check_access("DevTools")
	async def test_config(self, interaction: discord.Interaction):
		"""
		[DEV] Tests the server configuration and channel retrieval.

		**Permissions:**
		- `Developer`
		"""
		await send_response(interaction, "Starting test.", ephemeral=True)
		try:
			config = ConfigData().get_key(interaction.guild.id, "modchannel")
		except Exception as e:
			logging.error(e, exc_info=True)
			config = None
		if config is None:
			await send_message(interaction.channel, "Failed to retrieve channel")
			return
		await send_message(interaction.channel, "successfully tested Config, no errors found")

	@app_commands.command(name="test_channel", description="[DEV] Queues 1000 channel fetches to stress-test retrieval.")
	@AccessControl().check_access("DevTools")
	async def test_channel(self, interaction: discord.Interaction):
		"""
		[DEV] Queues 1000 channel fetches to stress-test the API and bot's handling.

		**Permissions:**
		- `Developer`
		"""
		await send_response(interaction, "Starting channel fetch test.", ephemeral=True)
		async def test_fetch():
			await self.bot.fetch_channel(interaction.channel.id)
			await asyncio.sleep(0.1)


		for i in range(1000):
			if i == 999:
				queue().add(test_fetch())
				continue
			queue().add(test_fetch())

		await send_response(interaction, "Queued 1000 channel fetches.", ephemeral=True)

	@app_commands.command(name="reload_access", description="[DEV] Reloads the access control lists from the database.")
	@AccessControl().check_access("DevTools")
	async def reload_access(self, interaction: discord.Interaction):
		"""
		[DEV] Reloads the access control lists (staff, blacklists) from the database.

		**Permissions:**
		- `Developer`
		"""
		AccessControl().reload()
		await send_response(interaction, "Access control reloaded.", ephemeral=True)



	async def find_ban_id(self, channel) :
		history = channel.history(limit=None, oldest_first=True)
		try :
			async for message in history :
				if len(message.embeds) < 1 :
					logging.info(f"Message {message.id} has no embeds ({len(message.embeds)})")
					continue
				embed = message.embeds[0]
				try:
					match = re.search(r'ban ID: (\d+)', embed.footer.text)
				except:
					match = None
				if not match :
					logging.warning(f"Failed to extract ban id from {embed.footer.text}")
					continue
				ban_id = int(match.group(1))
				ban = BanTransactions().get(ban_id, override=True)
				if ban is None :
					logging.warning(f"Ban ID {ban_id} not found in database")
					continue
				BanTransactions().update(ban_id, message=message.id, created_at=message.created_at if not ban.created_at else ban.created_at)

		except discord.NotFound :
			pass
async def setup(bot: commands.Bot) :
	await bot.add_cog(DevTools(bot))
