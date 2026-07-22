import logging

import discord
from discord.ext import commands
from discord_py_utilities.messages import send_message

from classes.access import AccessControl
from classes.ban.BanChecker import BanChecker, BanCheckerStatus
from classes.bans import Bans
from classes.configdata import ConfigData
from classes.queue import queue
from database.current import Servers
from database.transactions.BanTransactions import BanTransactions
from database.transactions.ServerTransactions import ServerTransactions
from view.buttons.baninform import BanInform
from view.buttons.banoptionbuttons import BanOptionButtons


class BanEvents(commands.Cog) :

	def __init__(self, bot: commands.Bot) :
		self.bot = bot
		self.bot.add_view(BanOptionButtons())
		self.bot.add_view(BanInform(Bans()))

	# ============================================================
	@commands.Cog.listener()
	async def on_member_ban(self, guild, user) :
		"""informs other servers an user is banned and updates banlist"""
		logging.info(f"Banned {user.name} from {guild.name}")
		bot = self.bot
		# Check if user is a bot
		if user == bot.user:
			logging.warning(f"I was banned in {guild.name}")
			return
		if user.bot:
			logging.warning(f"{user} is a bot, not storing.")
			return

		# Check if old ban entry exists, and delete it to prevent data from mixing - this only gets triggered if the user is banned again!
		ban_entry = BanTransactions().get(user.id + guild.id, override=True)
		if ban_entry is not None :
			BanTransactions().delete_permanent(ban_entry)

		# fetch ban entry
		ban: discord.BanEntry = await guild.fetch_ban(user)
		mod_channel = bot.get_channel(ConfigData().get_key_or_none(guild.id, "modchannel" ))

		# Check if modchannel is set, else just log it.
		if mod_channel is None:
			logging.warning(f"{guild.name}({guild.id}) doesn't have modchannel set.")
			queue().add(send_message(guild.owner, f"{guild.name}({guild.id}) doesn't have modchannel set. Please set it using the /Config change command."), priority=2)
			return

		# Hidden server: record the ban but never broadcast or prompt.
		if ServerTransactions().is_hidden(guild.id):
			await Bans().add_ban(user.id, guild.id, ban.reason, "Unknown")
			return

		# Lightweight PRE-CHECK only: short_run() runs just the cheap, string-only auto-hide rules
		# (cross-ban, low-value, migrated) - no flagged-term DB lookups or staff/PII scans, so we don't
		# burn resources on every ban. The action buttons below do the REAL, full check when a
		# moderator acts. BanChecker is the single source of truth; this path keeps no rules of its own.
		ban_checker = BanChecker(bot, ban)
		await ban_checker.short_run()

		# Only a definitive auto-hide verdict (cross-ban, low-value, migrated -> HIDE) short-circuits
		# here: evaluate_ban records it as hidden and we stop. Everything else falls through to the
		# buttons.
		if ban_checker.get_status() == BanCheckerStatus.HIDE :
			await ban_checker.evaluate_ban(guild, server_only=False)
			return

		# PREMIUM: automatically mirror a shareable ban into the owner's other servers.
		logging.info(ConfigData().get_key(guild.id, "cross_ban", False))
		if ConfigData().get_key(guild.id, "cross_ban", False) is True and AccessControl().is_premium(guild.id):
			logging.info("Cross-ban with premium")
			servers = ServerTransactions().get_owners_servers(owner_id=guild.owner.id)
			server_names = []
			for server in servers :
				logging.info(f"Premium cross-ban with server {server.name} ({server.id})")
				queue().add(self.cross_ban(server, guild, user))
				server_names.append(server.name)
			queue().add(send_message(mod_channel, f"Cross-banned user {user}({user.id}) in servers: {', '.join(server_names)}"), priority=0)

		# Not auto-hidden: always show the review buttons. They run the REAL check and persist the ban
		# when a moderator acts, so nothing is written here.
		logging.info("starting to update banlist and informing other servers")
		await ban_checker.send_review_prompt(guild)


	# ============================================================
	async def cross_ban(self, server: Servers, guild, user) :
		if server.id == guild.id :
			return
		target_guild = self.bot.get_guild(server.id)
		if target_guild is None :
			target_guild = await self.bot.fetch_guild(server.id)
		if target_guild is None :
			logging.warning(f"Could not find guild {server.id} to cross-ban {user}")
			return
		try :
			await target_guild.ban(user, reason=f"Cross-ban from {guild.name} with ban id: {user.id + guild.id}",
			                       delete_message_days=0)
			logging.info(f"Cross-banned {user} in {target_guild.name}({target_guild.id})")
		except discord.Forbidden :
			logging.warning(f"Missing permissions to cross-ban {user} in {target_guild.name}({target_guild.id})")
			return
		except discord.HTTPException as e :
			logging.error(f"HTTP Exception when cross-banning {user} in {target_guild.name}({target_guild.id}): {e}")
			return

async def setup(bot) :
	await bot.add_cog(BanEvents(bot))
