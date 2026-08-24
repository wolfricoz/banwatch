"""This class generates the ban list, with functions to update it, and to check for similar names"""
import asyncio
import logging
import os
import re
import time
from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord_py_utilities.exceptions import NoChannelException, NoPermissionException
from discord_py_utilities.invites import check_guild_invites
from discord_py_utilities.messages import send_message

from classes.appeal import inform_user
from classes.ban.ban_channel import SLOW_COOLDOWN, UNREACHABLE, UNSET, resolve_ban_channel, warn_missing_ban_channel
from classes.configdata import ConfigData
from classes.queue import queue
from classes.rpsec import RpSec
from classes.server import Server
from classes.singleton import Singleton
from data.config.mappings import Channels
from database.current import BanMessages, Proof
from database.transactions.BanMessageTransactions import BanMessageTransactions
from database.transactions.BanTransactions import BanTransactions
from database.transactions.ProofTransactions import ProofTransactions
from database.transactions.ServerTransactions import ServerTransactions
from view.buttons.baninform import BanInform


class Bans(metaclass=Singleton) :

	def __init__(self) :
		pass

	# ============================================================
	async def update(self, bot, override=False) :
		"""Updates the ban list"""
		guild: discord.Guild
		known_guilds = ServerTransactions().get_all()
		count = 0
		for guild in bot.guilds :
			try :
				if count % 10 == 0 :
					logging.info(f"Updating guilds... {count}/{len(bot.guilds)}")
					await asyncio.sleep(0)
				count += 1
				# Logged per guild, not per 10: if a guild stalls, the last line printed names it.
				logging.debug(f"[{count}/{len(bot.guilds)}] Processing {guild.name}({guild.id})")
				if guild.id in known_guilds :
					known_guilds.remove(guild.id)
				try :
					ServerTransactions().add(guild.id, guild.owner.name if guild.owner else 'unknown', guild.name,
					                         len(guild.members), None)
					await Bans().check_guild_invites(bot, guild)
				except Exception as e :
					logging.error(f"Error processing guild {guild.id}: {e}")
				await Bans().check_guild_bans(bot, guild)
			except Exception as e :
				logging.warning(f"Error processing guild {guild.id}: {e}")
		logging.info(
			f"Finished updating {count}/{len(bot.guilds)} guilds. {len(known_guilds)} guilds no longer known, removing...")

		count = 0
		g_count = len(known_guilds)
		for k in known_guilds :
			if count % 10 == 0 :
				logging.info(f"cleaning up guilds... {count}/{g_count}")
				await asyncio.sleep(0)
			count += 1

			ServerTransactions().delete_soft(k)
		await BanTransactions().populate_cache()
		logging.info('Finished updating bans.')

	# ============================================================
	def create_ban_id(self, user_id, guild_id) :
		return user_id + guild_id

	# ============================================================
	async def inform_server(self, bot: commands.Bot, guild: discord.Guild, banembed: discord.Embed, ban_id: int) :

		# banembed names the banned user and quotes the ban reason: it goes to the mod channel or
		# nowhere. Without one, the receiving server is told - in a random channel we can reach -
		# that it is missing out on ban reports, with no ban details in that warning.
		modchannel = await resolve_ban_channel(guild)
		if modchannel is None :
			await warn_missing_ban_channel(guild, source="broadcast", cooldown=SLOW_COOLDOWN)
			return
		options = BanInform(ban_class=Bans(), ban_id=ban_id)
		try :
			message = await send_message(modchannel, embed=banembed, view=options)
		except (discord.Forbidden, discord.HTTPException, NoPermissionException, NoChannelException) as e :
			logging.warning(f"Could not inform {guild.name}({guild.id}) about ban {ban_id}: {e}")
			await warn_missing_ban_channel(guild, problem=UNREACHABLE, source="broadcast",
			                               cooldown=SLOW_COOLDOWN, exclude=modchannel)
			return
		if message is None :
			# send_message swallows Forbidden in its default error mode and returns None; without
			# this guard the next line raises AttributeError inside the queue.
			logging.warning(f"No message returned when informing {guild.name}({guild.id}) about ban {ban_id}")
			return
		BanMessageTransactions().add_ban_message(ban_id, guild.id, message.id)

	# ============================================================
	async def check_guilds(self, interaction, bot, guild, user, banembed, wait_id, open_thread=False, verified=False,
	                       silent=False) :
		# approved_channel = bot.get_channel(bot.APPROVALCHANNEL)
		# await Bans().change_ban_approval_status(wait_id, True, verified=verified)
		# await self.send_to_ban_channel(approved_channel, banembed, guild, user, bot, wait_id)
		# return

		approved_channel = bot.get_channel(bot.APPROVALCHANNEL)
		count = 0
		for guilds in bot.guilds :
			count += 1
			if count % 5 == 0 :
				# To prevent locking up the event loop for too long, we yield control every 5 iterations to allow other tasks to run.
				await asyncio.sleep(0)
			if guilds.id == guild.id :
				continue
			if ConfigData().get_key(guilds.id, "receive_all", False) is True :
				queue().add(self.inform_server(bot, guilds, banembed, wait_id, ), priority=0)
			if user in guilds.members and not silent :
				queue().add(self.inform_server(bot, guilds, banembed, wait_id), priority=0)
		await Bans().change_ban_approval_status(wait_id, True, verified=verified)
		if interaction is not None :
			await interaction.message.delete()
		if not silent :
			queue().add(inform_user(guild, user), 0)

		queue().add(self.send_to_ban_channel(approved_channel, banembed, guild, user, bot, wait_id))

	# ============================================================
	async def send_to_ban_channel(self, approved_channel, banembed, guild, user, bot: commands.Bot,
	                              wait_id) :
		approved_message = await approved_channel.send(embed=banembed)
		BanTransactions().update(wait_id, message=approved_message.id)
		BanMessageTransactions().add_ban_message(ban_id=wait_id, guild_id=guild.id, message_id=approved_message.id)

		dev_guild: discord.Guild = bot.get_guild(bot.SUPPORTGUILD)

		queue().add(self.open_thread(user, guild, approved_message, dev_guild, bot), priority=1)

	# ============================================================
	async def open_thread(self, user, guild, approved_message, dev_guild: discord.Guild, bot) :
		rpsec = dev_guild.get_thread(RpSec.get_user(user.id))
		evidence_channel = bot.get_channel(bot.BANCHANNEL)
		wait_id = guild.id + user.id
		mod_channel = guild.get_channel(int(ConfigData().get_key(guild.id, "modchannel")))
		try :
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
			entries = ProofTransactions().get(ban_id=wait_id)
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
		except Exception as e :
			logging.warning(f"Failed to create thread for ban {wait_id} in {guild.name}: {e}")

	# ============================================================
	async def check_previous_bans(self, original_message, dev_guild: discord.Guild, user_id) -> list[discord.Message] :
		ban_record = BanTransactions().get_all_user(user_id)

		ban_channel: discord.TextChannel = dev_guild.get_channel(int(os.getenv("APPROVED")))
		bans = []

		for ban in ban_record :
			if ban.message :
				message = await ban_channel.fetch_message(ban.message)
				bans.append(message)
		return bans

	# ============================================================
	async def create_invite(self, bot: commands.AutoShardedBot | commands.Bot, guild: discord.Guild,
	                        force_new: bool = False) -> str :
		invite = None
		if not force_new :

			server = ServerTransactions().get(guild.id)
			if server :
				invite = server.invite

		channel = await ConfigData().get_channel(guild, Channels.INVITE, optional=True)
		inv = await check_guild_invites(bot, guild, invite, channel=channel)
		return inv

	# ============================================================
	def get_ban_id(self, embed: discord.Embed) :
		match = re.search(r'ban ID: (\w+)', embed.footer.text)
		return match.group(1) if match else None

	# ============================================================
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
				BanMessageTransactions().add_ban_message(ban_id, channel.guild.id, message.id)
				return message, embed
		return None, None

	# ============================================================
	async def revoke_bans(self, bot: commands.Bot, ban_id, reason, staff=False) :
		ban_messages = BanMessageTransactions().get_by_ban_id(ban_id=ban_id)
		ban_message: BanMessages

		for ban_message in ban_messages :
			guild = bot.get_guild(ban_message.server_id)
			if guild is None :
				guild = bot.fetch_guild(ban_message.server_id)
			if guild is None :
				logging.error(f"Guild {ban_message.server_id} not found for ban message {ban_message.message_id}")
				continue
			channel = await ConfigData().get_channel(guild, "modchannel")
			if channel is None :
				logging.info("No modchannel found, skipping")
				continue

			queue().add(self.delete_message(channel, ban_message.message_id, reason=reason), priority=0)
			BanMessageTransactions().delete_bm(int(ban_message.message_id))

		if staff :
			# A staff revoke retracts the whole verdict, not just the broadcast, so the ban goes
			# back to square one and in front of staff again. This sits OUTSIDE the message loop
			# on purpose: it used to run per ban message, which meant a ban with no broadcast
			# messages left - or one whose mod channels were all unreachable - kept its approved
			# flag and never returned to the queue. The non-staff callers (unban, and the hide
			# buttons, which have just set hidden=True) only want the messages pulled.
			await self.return_to_queue(bot, int(ban_id))

	# ============================================================
	async def return_to_queue(self, bot: commands.Bot, ban_id: int) -> bool :
		"""Resets a ban to pending - approved, verified and hidden all false - and re-posts it to
		the staff review queue.

		:return: True if the ban was reset and queued for review.
		"""
		from classes.tasks import queue_ban_for_review
		ban = BanTransactions().update(ban_id, approved=False, verified=False, hidden=False)
		if not ban :
			logging.warning(f"Cannot return ban {ban_id} to the review queue: ban not found.")
			return False
		logging.info(f"Ban {ban_id} reset to pending and returned to the review queue.")
		return await queue_ban_for_review(bot, ban)

	# ============================================================
	async def delete_message(self, channel: discord.TextChannel, message_id, reason=None) :
		try :
			message = await channel.fetch_message(message_id)
			if reason :
				await message.reply(f"Ban `{message.embeds[0].title}` revoked. Reason:\n{reason}")

			await message.delete()
			logging.info(f"Deleted ban message {message_id} in {channel.guild.name}")
		except discord.NotFound :
			logging.info(f"Ban message {message_id} not found in {channel.guild.name}, may have already been deleted")
		except discord.Forbidden :
			logging.error(f"Missing permissions to delete ban message {message_id} in {channel.guild.name}")
		except Exception as e :
			logging.error(f"Error deleting ban message {message_id} in {channel.guild.name}: {e}")

	# ============================================================
	
	async def check_guild_bans(self, bot: commands.AutoShardedBot, guild: discord.Guild) :
		if not guild :
			logging.error("check_guild_bans called without a guild")
			return
		me = guild.me
		if me is None :
			try :
				me = await guild.fetch_member(bot.user.id)
			except (discord.NotFound, discord.HTTPException) as e :
				logging.warning(f"Could not resolve bot member in {guild.name}({guild.id}), skipping: {e}")
				return

		if not me.guild_permissions.ban_members :
			logging.warning(
				f"No ban_members permission in {guild.name}({guild.id}), skipping guild (bans left untouched)")
			# Runs on every sweep, so throttle: staff hear about this at most once an hour.
			from classes.permissions_notice import PermissionNotice
			await PermissionNotice.notify(
				guild, missing=["ban_members"], purpose="apply shared bans in your server", throttle=True)
			return

		db_server = ServerTransactions().get(guild.id)
		if db_server and db_server.hidden is True :
			return

		modchannel = await resolve_ban_channel(guild)
		if not modchannel :
			logging.info(f"No usable modchannel for {guild.name}({guild.id}), skipping bans")
			# The sweep is the only thing that would ever notice, and it says nothing. Tell the
			# server - once a day, in a random channel we can reach - that its bans are going
			# nowhere. No ban details: the channel may be public.
			configured = ConfigData().get_key_or_none(guild.id, Channels.MOD_CHANNEL)
			await warn_missing_ban_channel(
				guild, problem=UNSET if not configured else UNREACHABLE, source="sweep",
				cooldown=SLOW_COOLDOWN)
			return

		count = 0
		server = Server(guild.id)
		scanned = 0
		scan_start = time.perf_counter()

		async for banentry in guild.bans(limit=None) :
			scanned += 1
			if scanned % 250 == 0 :
				logging.info(
					f"Scanned {scanned} bans in {guild.name}({guild.id}) "
					f"({time.perf_counter() - scan_start:.1f}s, {count} new)")
				await asyncio.sleep(0)

			if banentry.user.bot :
				continue
			if server.check_ban(banentry.user.id) :
				continue
			from classes.ban.BanChecker import BanChecker
			ban_checker = BanChecker(bot, banentry)
			await ban_checker.run()
			await ban_checker.evaluate_ban(guild, server_only=True)

			count += 1
			if count % 25 == 0 :
				logging.info(f"Found {count} new bans so far in {guild.name}({guild.id})")
				await asyncio.sleep(0)

		missed_targets = server.check_missed_ids()
		removed = server.remove_missing_ids(missed_targets)

		logging.info(
			f"Found {count} new bans in {guild.name}({guild.id}) after scanning {scanned} in "
			f"{time.perf_counter() - scan_start:.1f}s. Removed {removed}/{len(missed_targets)} stale bans.")

	INVITE_TIMEOUT = 30

	# ============================================================
	async def check_guild_invites(self, bot: commands.AutoShardedBot, guild: discord.Guild) :
		try :
			await asyncio.wait_for(self._resolve_guild_invite(bot, guild), timeout=self.INVITE_TIMEOUT)
		except asyncio.TimeoutError :
			logging.warning(
				f"Invite resolution for {guild.name}({guild.id}) exceeded {self.INVITE_TIMEOUT}s "
				f"(likely rate limited), skipping - guild keeps its existing invite.")

	# ============================================================
	async def _resolve_guild_invite(self, bot: commands.AutoShardedBot, guild: discord.Guild) :
		guild_record = ServerTransactions().get(guild.id)
		if guild_record and guild_record.invite :
			try :
				await bot.fetch_invite(guild_record.invite)
				return
			except discord.HTTPException :
				# NotFound subclasses HTTPException, so this covers the expired case too.
				logging.info(f"{guild.name}({guild.id})'s invite expired, creating a new one.")

		# No stored invite reaches here silently, which is what made this look like a hang. Say so.
		logging.info(f"Creating a new invite for {guild.name}({guild.id})")

		me = guild.me
		for channel in guild.channels :
			# Only text channels can produce invites; categories return 400 and everything else is
			# wasted calls. permissions_for reads the local cache, so channels we cannot invite from
			# are skipped without touching the API at all - this is what removes the rate limiting.
			if not isinstance(channel, discord.TextChannel) :
				continue
			if me is not None and not channel.permissions_for(me).create_instant_invite :
				continue
			try :
				invite = await channel.create_invite(reason="Banwatch invite")
			except discord.Forbidden :
				continue
			except discord.HTTPException as e :
				logging.debug(f"Could not create invite in #{channel.name} ({guild.id}): {e}")
				continue
			ServerTransactions().update(guild.id, invite=invite.url)
			logging.info(f"Created invite for {guild.name}({guild.id})")
			return

		# Nothing could be created - fall back to an existing invite if the guild has one.
		try :
			invite = (await guild.invites())[0]
			ServerTransactions().update(guild.id, invite=invite.url)
			logging.info(f"Reused existing invite for {guild.name}({guild.id})")
		except discord.Forbidden :
			logging.info(f"No permission to fetch invites in {guild.name}({guild.id})")
		except IndexError :
			logging.info(f"{guild.name}({guild.id}) has no invites.")
		except Exception as e :
			logging.error(f"Error creating invite for {guild.name}({guild.id}): {e}")

	# ============================================================
	async def add_ban(self, user_id, guild_id, reason, staff, hidden=False, approved=False, remove_deleted=True,
	                  status="Not set") :
		"""Adds a ban to the database"""
		if reason is None or reason == "" or reason.lower() == "none" :
			hidden = True
			reason = "No reason given"

		if reason.lower().startswith('[hidden]') :
			hidden = True
			reason = reason[8 :]
		logging.info(
			f"Adding ban for {user_id} in {guild_id} with reason: {reason} and approval status: {approved} (status: {status})")
		return BanTransactions().add(user_id, guild_id, reason, staff, hidden=hidden, approved=approved,
		                             remove_deleted=remove_deleted)

	# ============================================================
	async def delete_ban(self, user_id, guild_id, permanent=False) :
		"""Removes a ban from the database"""

		if permanent :
			BanTransactions().delete_permanent(user_id + guild_id)
		BanTransactions().delete_soft(user_id + guild_id)

	# ============================================================
	async def change_ban_approval_status(self, ban_id: int, status: bool, verified=False, hidden=None) :
		"""Approving or verifying a ban must never touch its visibility: hidden defaults to None so
		update() leaves the flag alone. It used to default to False, which meant every approval and
		every verification silently un-hid a ban staff had hidden. Pass hidden explicitly to change it."""
		BanTransactions().update(ban_id, approved=status, verified=verified, hidden=hidden)

	# ============================================================
	async def get_user_bans(self, user_id) :
		return BanTransactions().get_all_user(user_id)

	# ============================================================
	async def change_ban_reason(self, ban_id: int, reason: str, staff: str | None = "unknown") :
		"""
		Alters the ban reason for a ban, this is done to ensure that the ban follows the banwatch guidelines; only by banwatch staff!
		"""
		BanTransactions().update(ban_id, reason=reason, edited=datetime.now(tz=timezone.utc), edited_by=staff)
