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
from database.databaseController import BanDbTransactions, DatabaseTransactions, FlaggedTermsTransactions, \
	ServerDbTransactions, \
	StaffDbTransactions
from view.modals.inputmodal import send_modal
from discord.utils import get

OWNER = int(os.getenv("OWNER"))
GUILD = int(os.getenv("GUILD"))

SUPPORT_GUILD = discord.Object(GUILD)


class dev(commands.GroupCog, name="dev") :

	def __init__(self, bot: commands.Bot) :
		self.bot = bot

	async def inform_server(self, guild, banembed) :
		config = ConfigData().get_key(guild.id, "modchannel")
		modchannel = self.bot.get_channel(int(config))
		await modchannel.send(embed=banembed)

	@app_commands.command(name="updatecommands", description="[DEV] Unloads and syncs commands again", )
	@AccessControl().check_access("dev")
	async def update_commands(self, interaction: discord.Interaction) :
		queue().add(self.bot.tree.sync(), priority=2)
		await send_response(interaction,"Command sync queue, high priority queue.")

	@app_commands.command(name="stats", description="View banwatch's stats!", )
	async def stats(self, interaction: discord.Interaction) :
		with open('countbans.txt', 'w') :
			pass

		stats = {
			"servers_total" : ServerDbTransactions().count(),
			"bans_total"    : BanDbTransactions().count(),
			"verified_bans" : BanDbTransactions().count(result_type="verified"),
			"deleted_bans"  : BanDbTransactions().count(result_type="deleted"),
			"hidden_bans"   : BanDbTransactions().count(result_type="hidden"),
			"available"     : BanDbTransactions().count(result_type="available"),
			"queue-status"  : queue().status()
		}
		embed = discord.Embed(title="Banwatch's stats")
		for i, v in stats.items() :
			embed.add_field(name=i, value=v, inline=False)
		await send_message(interaction.channel, embed=embed)

	@app_commands.command(name="loadflaggedterms", description="[DEV] Loads old watchlist into flagged terms", )
	@AccessControl().check_access("dev")
	async def update_flagged_terms(self, interaction: discord.Interaction) :
		checklist = await Configer.get_checklist()
		for word in checklist :
			try:
				FlaggedTermsTransactions.add(term=word, action='review')
			except Exception as e:
				logging.warning(f"could not load {word} into flagged terms: {e}")

		await send_response(interaction,f"Old watchlist flagged terms have been successfully loaded. loaded: ||{', '.join(checklist)}||")


	@app_commands.command(name="announce", description="[DEV] Send an announcement to all guild owners")
	@AccessControl().check_access("dev")
	async def announce(self, interaction: discord.Interaction) :
		message = await send_modal(interaction, "What is the announcement?", "Announcement", 1700)
		if interaction.user.id != 188647277181665280 :
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
						f"Banwatch could not send the announcement to your modchannel in {guild.name}, please check the mod channel settings. You can setup your modchannel with: ```/config change option:Mod channel channel:```")
					await guild.owner.send(announcement)
				except Exception as e :
					await interaction.channel.send(f"Error sending to {guild}({guild.owner}): {e}")

	@app_commands.command(name="leave_server", description="[DEV] Leave a server")
	@AccessControl().check_access("dev")
	async def leave_server(self, interaction: discord.Interaction, guildid: int) :
		guild = self.bot.get_guild(guildid)
		await guild.leave()
		await send_response(interaction,f"Left {guild}")

	@app_commands.command(name="blacklist_server", description="[DEV] Blacklist a server")
	@AccessControl().check_access("dev")
	async def blacklist_server(self, interaction: discord.Interaction, guildid: str) :
		guildid = int(guildid)
		guild = self.bot.get_guild(guildid)
		await Configer.add_to_blacklist(guildid)
		await guild.leave()
		await send_response(interaction,f"Blacklisted {guild}")

	@app_commands.command(name="unblacklist_server", description="[DEV] Remove a server from the blacklist")
	@AccessControl().check_access("dev")
	async def unblacklist_server(self, interaction: discord.Interaction, guildid: str) :
		guildid = int(guildid)
		await Configer.remove_from_blacklist(guildid)
		await send_response(interaction,f"Unblacklisted {guildid}")

	# blacklist user goes here
	@app_commands.command(name="blacklist_user", description="[DEV] Blacklist a user")
	@AccessControl().check_access("dev")
	async def blacklist_user(self, interaction: discord.Interaction, userid: str) :
		userid = int(userid)
		await Configer.add_to_user_blacklist(userid)
		await send_response(interaction, f"Blacklisted {userid}")

	@app_commands.command(name="unblacklist_user", description="[DEV] Remove a user from the blacklist")
	@AccessControl().check_access("dev")
	async def unblacklist_user(self, interaction: discord.Interaction, userid: str) :
		userid = int(userid)
		await Configer.remove_from_user_blacklist(userid)
		await send_response(interaction, f"Unblacklisted {userid}")

	@app_commands.command(name="checklist",
	                      description="[DEV] Manage the checklist, these bans will be checked due to controversial reasons")
	@app_commands.choices(operation=[
		Choice(name="add", value="add"),
		Choice(name="remove", value="remove"),
		Choice(name="list", value="list")
	],
	action=[
		Choice(name="review", value="review"),
		Choice(name="block", value="block"),
		Choice(name="countreview", value="countreview"),
		Choice(name="countblock", value="countblock"),
	])
	@AccessControl().check_access(role="dev")
	async def flaggedterms(self, interaction: discord.Interaction, operation: Choice[str], term: str, action: Choice[str], regex: bool = False) :
		match operation.value :
			case "add" :
				result = FlaggedTermsTransactions.add(term=term, action=action.value, regex=regex)
				if not result :
					return await send_response(interaction, f"Failed to add {term}")

				return await send_response(interaction,f"Added {term} to the flagged terms list with action {action.value} and regex status {regex}", ephemeral=True)

			case "remove" :
				result = FlaggedTermsTransactions.delete(term)
				if not result :
					return await send_response(interaction, f"Failed to remove {term}")
				return await send_response(interaction,f"Removed {term} from the checklist", ephemeral=True)

			case "list" :
				await send_response(interaction, "Fetching flagged words", )
				flaggedWords = FlaggedTermsTransactions.get_all()
				result = ""
				for word in flaggedWords :
					result += f"Term: {word.term} Action: {word.action} Regex: {word.regex}\n"
				
				
				with open('flaggedwords.txt', 'w') as file:
					file.write("All flagged words:\n")
					file.write(result)

				return await send_message(interaction.channel, "Here is a list of all flagged words:", files=[discord.File(file.name)])
		return None

	@app_commands.command(name="backup")
	@AccessControl().check_access("dev")
	async def copy(self, interaction: discord.Interaction, evidence_only: bool = False) :
		await send_response(interaction, "Backup Started", ephemeral=True)
		dev_guild: discord.Guild = self.bot.get_guild(int(os.getenv("GUILD")))
		print(f"dev_guild: {dev_guild}")

		backup_guild: discord.Guild = self.bot.get_guild(int(os.getenv("BACKUPGUILD")))
		print(f"backup_guild: {backup_guild}")

		ban_channel: discord.TextChannel = dev_guild.get_channel(int(os.getenv("APPROVED")))
		print(f"ban_channel: {ban_channel}")

		evidence_channel: discord.TextChannel = dev_guild.get_channel(int(os.getenv("EVIDENCE")))
		print(f"evidence_channel: {evidence_channel}")
		backupsection = get(backup_guild.categories, name="backup")
		if backupsection is None :
			backupsection = await backup_guild.create_category_channel("backup",
			                                                           overwrites={
				                                                           backup_guild.default_role : discord.PermissionOverwrite(
					                                                           read_messages=False)})

		pending_removal: list[Coroutine] = [channel.delete() for channel in backupsection.channels]

		# Instead of static channels, we will now make channels when the bot is ran.

		backupevidence = await backup_guild.create_text_channel(f"evidence-{datetime.now().strftime('%m-%d-%Y')}",
		                                                        category=backupsection)
		ban_history = ban_channel.history(limit=None, oldest_first=True)
		evidence_history = evidence_channel.history(limit=None, oldest_first=True)
		bans = BanDbTransactions().get_all(override=True)
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
		backupbans = await backup_guild.create_text_channel(f"bans-{datetime.now().strftime('%m-%d-%Y')}",
		                                                    category=backupsection)
		async for message in ban_history :
			if len(message.embeds) < 1 :
				continue
			queue().add(
				backupbans.send(f"{message.content}",
				                files=[await attachment.to_file() for attachment in message.attachments],
				                embeds=message.embeds), 0)

	@app_commands.command(name="rebuild_evidence")
	@AccessControl().check_access("dev")
	async def rebuild_evidence(self, interaction: discord.Interaction, channel: discord.TextChannel, log: bool = False) :
		await send_response(interaction, "Rebuilding evidence channel", ephemeral=True)

		DatabaseTransactions().truncate("proof")
		evidence_history = channel.history(limit=None, oldest_first=True)
		async for message in evidence_history :
			if message.content.startswith("Evidence") is False :
				continue
			try :
				id = int(message.content.replace(":", "").split(" ")[2])
			except :
				logging.warning(f"Failed to extract id from {message.content}")
				continue
			ban = BanDbTransactions().get(id, override=True)
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

	@app_commands.command(name="rebuild_bans")
	@AccessControl().check_access("dev")
	async def rebuild_bans(self, interaction: discord.Interaction, channel: discord.TextChannel = None) :
		if channel is None :
			channel = interaction.client.get_channel(int(os.getenv("APPROVED")))

		await send_response(interaction, "Rebuilding bans channel", ephemeral=True)

		DatabaseTransactions().truncate("bans")
		await self.find_ban_id(channel)
		await interaction.followup.send(f"Rebuilding bans channel complete", ephemeral=True)

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
				ban = BanDbTransactions().get(ban_id, override=True)
				if ban is None :
					logging.warning(f"Ban ID {ban_id} not found in database")
					continue
				BanDbTransactions().update(ban_id, message=message.id, created_at=message.created_at if not ban.created_at else ban.created_at)

		except discord.NotFound :
			pass

	@app_commands.command(name="testban", description="[DEV] unbans and rebans the test account")
	@AccessControl().check_access("dev")
	async def testban(self, interaction: discord.Interaction, checklist: bool = True) :
		user = self.bot.get_user(474365489670389771)
		if user is None:
			user = await self.bot.fetch_user(474365489670389771)

		try :
			await interaction.guild.unban(user, reason="Test unban")
		except Exception as e :
			await send_message(interaction.channel, f"Failed to unban test account with reason: {e}")
			pass
		try :
			await interaction.guild.ban(user,
			                            reason=f"{'Test Ban that is longer than four words' if checklist else 'dev ban that is longer than four words'}")
		except AttributeError :
			user = await self.bot.fetch_user(474365489670389771)
			await interaction.guild.ban(user,
			                            reason=f"{'Test Ban that is longer than four words' if checklist else 'dev ban that is longer than four words'}")
		await send_response(interaction,"Test ban complete", ephemeral=True)

	@app_commands.command(name="pendingbans", description="[DEV] Lists all pending bans")
	@AccessControl().check_access("dev")
	async def pendingbans(self, interaction: discord.Interaction) :
		await pending_bans(self.bot)
		await send_response(interaction, "Checking for pending bans", ephemeral=True)

	@app_commands.command(name="refreshbans", description="[DEV] Refreshes the bans")
	@AccessControl().check_access("dev")
	async def refreshbans(self, interaction: discord.Interaction) :
		await Bans().update(self.bot, override=True)
		await send_response(interaction,"Bans refresh queued", ephemeral=True)

	@app_commands.command(name="add_staff", description="[DEV] Adds a staff member to the team")
	@app_commands.choices(role=[Choice(name=x, value=x.lower()) for x in ["Dev", "Rep"]])
	async def add_staff(self, interaction: discord.Interaction, user: discord.User, role: Choice[str]) :
		if interaction.user.id != int(os.getenv("OWNER")) :
			return await send_response(interaction, "You do not have permission to add staff members")
		StaffDbTransactions().add(user.id, role.value)
		await send_response(interaction, f"Staff member {user.mention} successfully added as a `{role.name}`!")
		AccessControl().reload()

	@app_commands.command(name="stop", description="[DEV] Shuts the bot down")
	async def quit(self, interaction: discord.Interaction) :
		if interaction.user.id != int(os.getenv("OWNER")) :
			return await send_response(interaction, "You do not have permission to add staff members")
		await self.bot.close()
		quit(0)

	@app_commands.command(name="remove_staff", description="[DEV] Remove a staff member from the team")
	@AccessControl().check_access("dev")
	async def remove_staff(self, interaction: discord.Interaction, user: discord.User) :
		StaffDbTransactions().delete(user.id)
		await send_response(interaction, f"Staff member {user.mention} successfully removed!")
		AccessControl().reload()

	@app_commands.command(name="test_config", description="[DEV] Tests if features are working correctly.")
	@AccessControl().check_access("dev")
	async def test_config(self, interaction: discord.Interaction):
		await send_response(interaction, "Starting test.", ephemeral=True)
		try:
			channel = await ConfigData().get_channel(interaction.guild)
		except Exception as e:
			logging.error(e, exc_info=True)
			channel = None
		if channel is None:
			await send_message(interaction.channel, "Failed to retrieve channel")
			return
		await send_message(interaction.channel, "successfully tested config, no errors found")



async def setup(bot: commands.Bot) :
	await bot.add_cog(dev(bot))
