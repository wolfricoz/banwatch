"""This class generates the ban list, with functions to update it, and to check for similar names"""
import logging
import os
import re

import discord
from discord.ext import commands
from discord_py_utilities.messages import send_message

from classes.appeal import inform_user
from classes.configdata import ConfigData
from classes.queue import queue
from classes.rpsec import RpSec
from classes.server import Server
from classes.singleton import Singleton
from database.current import Proof
from database.databaseController import BanDbTransactions, ProofDbTransactions, ServerDbTransactions
from view.buttons.baninform import BanInform


class Bans(metaclass=Singleton) :

	def __init__(self) :
		pass

	async def update(self, bot, override=False) :
		"""Updates the ban list"""
		guild: discord.Guild
		known_guilds = ServerDbTransactions().get_all()
		for guild in bot.guilds :
			if guild.id in known_guilds :
				known_guilds.remove(guild.id)
			ServerDbTransactions().add(guild.id, guild.owner.name, guild.name, len(guild.members), None)
			queue().add(Bans().check_guild_bans(guild), priority=0)
			queue().add(Bans().check_guild_invites(bot, guild), priority=0)
		for k in known_guilds :
			ServerDbTransactions().delete_soft(k)
		queue().add(BanDbTransactions().populate_cache(), priority=0)

	def create_ban_id(self, user_id, guild_id) :
		return user_id + guild_id

	async def inform_server(self, bot: commands.Bot, guild: discord.Guild, banembed: discord.Embed, ban_id: int) :
		modchannel_id = ConfigData().get_key(guild.id, "modchannel")
		modchannel = bot.get_channel(modchannel_id)
		if modchannel is None :
			await send_message(guild.owner,
			                   f"Mod channel not found in {guild.name} ({guild.id}). Current value: {modchannel_id}")
			return
		options = BanInform(ban_class=Bans(), ban_id=ban_id)
		queue().add(modchannel.send(embed=banembed, view=options), priority=0)

	async def check_guilds(self, interaction, bot, guild, user, banembed, wait_id, open_thread=False, verified=False) :
		approved_channel = bot.get_channel(bot.APPROVALCHANNEL)
		for guilds in bot.guilds :
			if guilds.id == guild.id :
				continue
			if user in guilds.members :
				queue().add(self.inform_server(bot, guilds, banembed, wait_id), priority=0)
		await Bans().change_ban_approval_status(wait_id, True, verified=verified)
		if interaction is not None :
			await interaction.message.delete()
		queue().add(inform_user(guild, user), 0)

		queue().add(self.send_to_ban_channel(approved_channel, banembed, guild, user, bot, wait_id))

	async def send_to_ban_channel(self, approved_channel, banembed, guild, user, bot: commands.Bot,
	                              wait_id) :
		approved_message = await approved_channel.send(embed=banembed)
		BanDbTransactions().update(wait_id, message=approved_message.id)
		dev_guild: discord.Guild = bot.get_guild(bot.SUPPORTGUILD)

		queue().add(self.open_thread(user, guild, approved_message, dev_guild, bot), priority=1)

	async def open_thread(self, user, guild, approved_message, dev_guild: discord.Guild, bot) :
		rpsec = dev_guild.get_thread(RpSec.get_user(user.id))
		evidence_channel = bot.get_channel(bot.BANCHANNEL)
		wait_id = guild.id + user.id
		mod_channel = guild.get_channel(int(ConfigData().get_key(guild.id, "modchannel")))

		thread = await approved_message.create_thread(name=f"Ban Information for {user.name}")
		logging.info(f"Created thread {thread.name} in {thread.guild.name}")
		if rpsec is not None :
			logging.info(f"User's RP Security thread: {rpsec.name}")
			await send_message(thread, f"User's RP Security thread: {rpsec.mention}")
		prev_bans = await self.check_previous_bans(approved_message, dev_guild, user.id)
		if prev_bans :
			logging.info(f"Previous bans for {user.name}: {prev_bans}")
			text_bans = '\n'.join([f"{ban.jump_url}" for ban in prev_bans])
			await send_message(thread, f"Previous bans for {user.name}:"
			                           f"\n{text_bans}")
		entries = ProofDbTransactions().get(ban_id=wait_id)
		if not entries :
			return
		await send_message(thread, f"## __Proof for {wait_id}__")
		evidence: Proof
		for evidence in entries :
			proof = '\n'.join(evidence.get_attachments())
			content = (f"**{evidence.ban_id}**:"
			           f"\n**ban reason**: {evidence.ban.reason}"
			           f"\n**Provided Proof**: {evidence.proof}"
			           f"\n**attachments:**\n {proof}")
			queue().add(send_message(thread, content))

	async def check_previous_bans(self, original_message, dev_guild: discord.Guild, user_id) -> list[discord.Message] :
		ban_record = BanDbTransactions().get_all_user(user_id)

		ban_channel: discord.TextChannel = dev_guild.get_channel(int(os.getenv("APPROVED")))
		bans = []

		for ban in ban_record :
			if ban.message :
				message = await ban_channel.fetch_message(ban.message)
				bans.append(message)
		return bans

	async def create_invite(self, guild: discord.Guild) :
		try :
			config = ConfigData().get_key(guild.id, "modchannel")
			invite = await guild.get_channel(config).create_invite(max_age=604800)
		except discord.Forbidden :
			invite = 'No permission'
		except Exception as e :
			invite = f'No permission/Error'
			logging.error(f"Error creating invite: {e}")

		return invite

	async def delete_message(self, message: discord.Message) :
		try :
			thread = await message.fetch_thread()
			await thread.delete()
		except :
			pass
		await message.delete()
		print(f"deleted {message.id}")

	def get_ban_id(self, embed: discord.Embed) :
		match = re.search(r'ban ID: (\w+)', embed.footer.text)
		return match.group(1) if match else None

	async def find_ban_record(self, bot, ban_id, channel=None) :
		"""This function searches through channels for messages with embeds matching the ban id, when found it returns the message and embed.
		:param bot:
		:param ban_id:
		:param channel:
		:return:
		"""
		if channel is None :
			channel = bot.get_channel(int(os.getenv("APPROVED")))

		async for message in channel.history() :
			if message.author.id != bot.user.id :
				continue
			if len(message.embeds) < 1 :
				continue
			embed = message.embeds[0]
			if not embed.footer.text :
				continue
			result = self.get_ban_id(embed)
			if result and int(ban_id) == int(result) :
				print(f"Found {message.id} in {channel.name} ({channel.guild.name})")
				return message, embed
		return None, None

	async def search_messages(self, bot, channel: discord.TextChannel, banid: str, reason: str) :
		"""

		:param bot:
		:param channel:
		:param banid:
		:param reason:
		:return:
		"""
		banid = str(banid)
		try :
			message, embed = await self.find_ban_record(bot, banid, channel)
		except discord.Forbidden :
			await channel.guild.owner.send(
				f"Banwatch does not have permission to view chat history or access to the channel in {channel.name} ({channel.guild}). Please give Banwatch the necessary permissions to revoke bans from the channel. This is to ensure that"
				f" the correct information is shared and bans with false information can be removed.")
			logging.error(f"Missing permissions to search messages in {channel.name} ({channel.guild})")
			return
		if message is None :
			return
		queue().add(self.delete_message(message), priority=2)
		queue().add(channel.send(f"Revoked ban `{embed.title}`! Reason: \n"
		                         f"{reason}"), priority=2)
		print(f"[revoke_ban] Queued deletion of {message.id} in {channel.name} ({channel.guild.name})")
		logging.info(f"[revoke_ban] Queued deletion of {message.id} in {channel.name} ({channel.guild.name})")

	async def revoke_bans(self, bot, banid, reason, staff=False) :
		print("revoking bans")
		for guild in bot.guilds :
			modchannel = ConfigData().get_key_or_none(guild.id, "modchannel")
			channel = bot.get_channel(modchannel)
			if channel is None :
				continue
			queue().add(self.search_messages(bot, channel, banid, reason))
		if staff :
			BanDbTransactions().update(int(banid), approved=False)
		channel = bot.get_channel(bot.APPROVALCHANNEL)
		queue().add(self.search_messages(bot, channel, banid, reason))

	async def check_guild_bans(self, guild: discord.Guild) :
		count = 0
		server = Server(guild.id)

		async for banentry in guild.bans(limit=None) :
			if banentry.user.bot :
				continue
			if server.check_ban(banentry.user.id) :
				continue
			await self.add_ban(banentry.user.id, guild.id, banentry.reason, guild.owner.name, approved=True)
			count += 1
		queue().add(server.remove_missing_ids(), priority=0)
		logging.info(f"Found {count} new bans in {guild.name}({guild.id})")

	async def check_guild_invites(self, bot: commands.AutoShardedBot, guild: discord.Guild) :
		guild_record = ServerDbTransactions().get(guild.id)
		invite: None | discord.Invite = None
		if guild_record and guild_record.invite :
			try :
				await bot.fetch_invite(guild_record.invite)
				return
			except discord.HTTPException or discord.NotFound :
				logging.info(f"{guild.name}'s invite expired, creating a new one.")
		try :
			for channel in guild.channels :
				try :
					invite = await channel.create_invite(reason="Banwatch invite")
				except discord.NotFound :
					continue
				ServerDbTransactions().update(guild.id, invite=invite.url)
				return
		except discord.Forbidden :
			logging.info(f"No permission to create invites in {guild.name}")
		try :
			invite: discord.Invite = (await guild.invites())[0]
			ServerDbTransactions().update(guild.id, invite=invite.url)
		except discord.Forbidden :
			logging.info(f"No permission to fetch invites in {guild.name}")
		except IndexError :
			logging.info(f"{guild.name} has no invites.")
		except Exception as e :
			logging.error(f"Error creating invite: {e}")

	async def add_ban(self, user_id, guild_id, reason, staff, hidden=False, approved=False, remove_deleted=True) :
		"""Adds a ban to the database"""
		if reason is None or reason == "" or reason.lower() == "none" :
			hidden = True
			reason = "No reason given"

		if reason.lower().startswith('[hidden]') :
			hidden = True
			reason = reason[8 :]
		logging.info(f"Adding ban for {user_id} in {guild_id} with reason: {reason} and approval status: {approved}")
		BanDbTransactions().add(user_id, guild_id, reason, staff, hidden=hidden, approved=approved,
		                        remove_deleted=remove_deleted)

	async def delete_ban(self, user_id, guild_id, permanent=False) :
		"""Removes a ban from the database"""

		if permanent :
			BanDbTransactions().delete_permanent(user_id + guild_id)
		BanDbTransactions().delete_soft(user_id + guild_id)

	async def change_ban_approval_status(self, ban_id: int, status: bool, verified=False) :
		BanDbTransactions().update(ban_id, approved=status, verified=verified)

	async def get_user_bans(self, user_id) :
		return BanDbTransactions().get_all_user(user_id)

