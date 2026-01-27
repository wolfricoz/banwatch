import discord
from discord.ext.commands import Bot, Cog
from discord_py_utilities.messages import send_message

from classes.access import AccessControl
from classes.configdata import ConfigData


class on_reaction_add(Cog) :

	def __init__(self, bot: Bot) :
		self.bot = bot

	@Cog.listener("on_raw_reaction_add")
	async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) :
		# Ignore reactions from the bot itself
		if payload.user_id == self.bot.user.id :
			return

		# Check if the guild is premium
		if not AccessControl().is_premium(payload.guild_id) :
			return

		# Fetch necessary objects
		guild = self.bot.get_guild(payload.guild_id)
		if not guild :
			return

		channel = guild.get_channel(payload.channel_id)
		if not channel :
			return

		try :
			message = await channel.fetch_message(payload.message_id)
		except discord.NotFound :
			return

		user = guild.get_member(payload.user_id)
		if not user :
			return

		# Your existing logic
		if len(message.embeds) < 1 :
			return

		embed = message.embeds[0]
		if not embed.footer or embed.footer.text.lower() != "bot trap button" :
			return

		modchannel_id = ConfigData().get_key(guild.id, "modchannel")
		if modchannel_id :
			modchannel = guild.get_channel(modchannel_id)
			if modchannel :
				await send_message(modchannel, f"Bottrap triggered by {user.name} ({user.id})")

		await guild.ban(user, reason="MemberLookup pressed the bot trap buttons.")


async def setup(bot: Bot) :
	await bot.add_cog(
		on_reaction_add(bot),
	)
