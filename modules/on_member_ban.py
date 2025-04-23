import logging
import re

import discord
from discord.ext import commands
from discord_py_utilities.messages import send_message

from classes.bans import Bans
from classes.configdata import ConfigData
from classes.queue import queue
from database.databaseController import BanDbTransactions, ServerDbTransactions
from view.buttons.baninform import BanInform
from view.buttons.banoptionbuttons import BanOptionButtons


class BanEvents(commands.Cog) :

	def __init__(self, bot: commands.Bot) :
		self.bot = bot
		self.bot.add_view(BanOptionButtons())
		self.bot.add_view(BanInform(Bans()))

	# TODO: When a user is banned, it doesn't seem to be sending the evidence to the right channel. Review this code, the on_member_unban and all underlying functions tomorrow.
	# TODO: Maybe refactor this for readability. This function is growing fast!
	@commands.Cog.listener()
	async def on_member_ban(self, guild, user) :
		"""informs other servers an user is banned and updates banlist"""
		print('ban event')

		bot = self.bot
		# Check if user is a bot
		if user == bot.user:
			logging.warning(f"I was banned in {guild.name}")
			return
		if user.bot:
			logging.info(f"{user} is a bot, not storing.")
			return
		# Check if old ban entry exists, and delete it to prevent data from mixing - this only gets triggered if the user is banned again!
		ban_entry = BanDbTransactions().get(user.id + guild.id, override=True)
		if ban_entry is not None :
			BanDbTransactions().delete_permanent(ban_entry)


		ban: discord.BanEntry = await guild.fetch_ban(user)
		# Check if the server is hidden
		if ServerDbTransactions().is_hidden(guild.id):
			await Bans().add_ban(user.id, guild.id, ban.reason, "Unknown")
			return
		# Check if the ban is a cross-ban
		match = re.match(r"Cross-ban from (?P<guild_name>.+?) with ban id: (?P<ban_id>\d+)", ban.reason)
		if match:
			logging.info("Cross-ban with no additional info, this ban has been hidden")
			await Bans().add_ban(user.id, guild.id, ban.reason, guild.owner.name, hidden=True)
			return
		# Check if the ban is a migrated ban
		if str(ban.reason).lower().startswith('[Migrated'):
			logging.info("Migrated ban, not prompting")
			await Bans().add_ban(user.id, guild.id, ban.reason, guild.owner.name,)

		mod_channel = bot.get_channel(int(ConfigData().get_key_or_none(guild.id, "modchannel")))
		if mod_channel is None:
			logging.warning(f"{guild.name}({guild.id}) doesn't have modchannel set.")
			await Bans().add_ban(user.id, guild.id, ban.reason, "No Modchannel Set", approved=False)
			return

		# check if ban has to be hidden
		if ban.reason is None or ban.reason in ["", "none", "Account has no avatar.", "No reason given."] or str(ban.reason).lower().startswith('[hidden]'):
			logging.info("silent or hidden ban/no reason, not prompting")
			await Bans().add_ban(user.id, guild.id, "Hidden Ban", "Unknown", hidden=True)
			if mod_channel is None :
				logging.error(f"{guild.name}({guild.id}) doesn't have modchannel set.")
				return
			await send_message(mod_channel, f"Hidden ban for {user}({user.id}).")
			return
		logging.info("starting to update banlist and informing other servers")
		view = BanOptionButtons()
		if mod_channel is None :
			logging.error(f"{guild.name}({guild.id}) doesn't have modchannel set.")
			await Bans().add_ban(user.id, guild.id, ban.reason, guild.owner.name)
			try :
				await guild.owner.send(
					"No moderation channel set, please setup your moderation channel using the /config commands. Your ban has not been broadcasted but has been recorded")
			except :
				for channel in guild.channels :
					try :
						await channel.send(
							"No moderation channel set, please setup your moderation channel using the /config commands. Your ban has not been broadcasted but has been recorded")
					except discord.NotFound or discord.Forbidden :
						continue
					return
			return

		embed = discord.Embed(title=f"Do you want to share {user}'s ({user.id}) ban with other servers?",
		                      description=f"{ban.reason}")
		embed.set_footer(text=f"{guild.id}-{user.id}")
		queue().add(mod_channel.send(embed=embed, view=view), priority=2)


async def setup(bot) :
	await bot.add_cog(BanEvents(bot))
