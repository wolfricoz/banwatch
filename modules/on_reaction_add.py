import discord
from discord.ext.commands import Cog, GroupCog, Bot
from discord_py_utilities.messages import send_message

from classes.access import AccessControl
from classes.configdata import ConfigData


class on_reaction_add(Cog) :

	def __init__(self, bot: Bot) :
		self.bot = bot

	@Cog.listener("on_reaction_add")
	async def on_reaction_add(self, reaction: discord.Reaction, user) :
		if not AccessControl().is_premium(reaction.message.guild.id):
			return
		if user == self.bot.user :
			return
		if len(reaction.message.embeds) < 1:
			return
		embed = reaction.message.embeds[0]
		if embed.footer.text.lower() != "Bot Trap Button" :
			return
		modchannel = reaction.message.guild.get_channel(ConfigData().get_key(reaction.message.guild.id, "modchannel"))
		await send_message(modchannel, f"Bottrap triggered by {user.name} ({user.id})")
		await reaction.message.guild.ban(user, reason="User pressed the bot trap buttons.")


async def setup(bot: Bot) :
	await bot.add_cog(
		on_reaction_add(bot),
	)
