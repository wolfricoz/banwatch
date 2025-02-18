import logging
import re

import discord
from discord.ext import commands

from classes.bans import Bans
from classes.configer import Configer
from classes.support.discord_tools import send_message
from database.databaseController import ServerDbTransactions
from view.buttons.baninform import BanInform
from view.buttons.banoptionbuttons import BanOptionButtons


class BanEvents(commands.Cog) :

	def __init__(self, bot: commands.Bot) :
		self.bot = bot
		self.bot.add_view(BanOptionButtons())
		self.bot.add_view(BanInform(Bans()))


	@commands.Cog.listener()
	async def on_member_ban(self, guild, user) :
		"""informs other servers an user is banned and updates banlist"""
		print('ban event')

		bot = self.bot
		if user == bot.user :
			logging.warning(f"I was banned in {guild.name}")
			return
		ban: discord.BanEntry = await guild.fetch_ban(user)
		if ServerDbTransactions().is_hidden(guild.id):
			await Bans().add_ban(user.id, guild.id, ban.reason, "Unknown")
			return
		match = re.match(r"Cross-ban from (?P<guild_name>.+?) with ban id: (?P<ban_id>\d+)", ban.reason)
		if match:
			logging.info("Cross-ban with no additional info, this ban has been hidden")
			await Bans().add_ban(user.id, guild.id, ban.reason, guild.owner.name, hidden=True)
			return
		mod_channel = bot.get_channel(int(await Configer.get(guild.id, "modchannel")))
		if ban.reason is None or ban.reason in ["", "none", "Account has no avatar.", "No reason given."] or str(
				ban.reason).lower().startswith('[silent]') or str(ban.reason).lower().startswith('[hidden]'):
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
		await mod_channel.send(embed=embed, view=view)


async def setup(bot) :
	await bot.add_cog(BanEvents(bot))
