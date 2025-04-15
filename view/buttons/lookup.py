import discord
from discord.ext import commands
from discord.ui import View
from discord_py_utilities.messages import send_message
from sqlalchemy.testing.suite.test_reflection import users

from classes.evidence import EvidenceController
from database.databaseController import ProofDbTransactions
from view.multiselect.selectban import SelectBan


class LookUp(View) :
	bot = None

	def __init__(self, user_id=None) :
		super().__init__(timeout=None)
		if not user_id :
			return
		entries = ProofDbTransactions().get(user_id=user_id)
		if not entries :
			self.evidence.disabled = True

	async def send_message(self, bot: commands.Bot, channel: discord.TextChannel, sr,
	                       user: discord.Member | discord.User, excess=True, override=False) :
		if len(sr) <= 0 or not sr :
			nfembed = discord.Embed(title=f"{user.name}({user.id})'s ban history.", description="No bans found.")
			await send_message(channel, embed=nfembed)
			return
		characters = 0
		count = 0
		bans = []
		embed = discord.Embed(title=f"{user.name}({user.id})'s ban history",
		                      description="Please ensure to reach out to the respective servers for proof or check the support server before taking any action.\n\nIf you ban based upon a ban, please include 'Cross-ban from (server-name):' in front of it.")
		embed.set_footer(text=f"{user.id}")
		for i, ban in enumerate(sr) :
			if count >= 10 :
				await send_message(channel, embed=embed, view=self)
				embed.clear_fields()
				count = 0
			count += 1
			guild = bot.get_guild(ban.gid)
			staff_data = f"approved: {ban.approved}, hidden: {ban.hidden}"

			created_at = ban.created_at.strftime(
				'%m/%d/%Y') if ban.message else 'pre-banwatch, please check with server owner.'
			embed.add_field(name=f"{guild.name} ({ban.guild.invite}) (ban_id: {ban.ban_id})",
			                value=f"{ban.reason}\n"
			                      f"verified: {'Yes' if ban.verified else 'No'}, date: {created_at}{f', {staff_data}' if override else ''}",
			                inline=False)
		sr = "\n".join(bans)

		if len(sr) == 0 :
			await send_message(channel, embed=embed, view=self)
			return
		await send_message(channel, embed=embed, view=self)
		while characters < len(sr) :
			await send_message(channel, sr[characters :characters + 1800])
			characters += 1800

	async def get_user_id(self, interaction: discord.Interaction) :
		embed = interaction.message.embeds[0]
		return int(embed.footer.text)

	@discord.ui.button(label="view evidence", style=discord.ButtonStyle.primary, custom_id="evidence")
	async def evidence(self, interaction: discord.Interaction, button: discord.ui.Button) :
		user_id = await self.get_user_id(interaction)
		entries = ProofDbTransactions().get(user_id=user_id)
		await EvidenceController().send_proof(interaction, entries, user_id)

	@discord.ui.button(label="Cross-ban", style=discord.ButtonStyle.danger, custom_id="Cross-ban")
	async def cross_ban(self, interaction: discord.Interaction, button: discord.ui.Button) :
		user_id = await self.get_user_id(interaction)
		await interaction.response.send_message("Please select which server you want to cross-ban from.", view=SelectBan(user_id), ephemeral=True)