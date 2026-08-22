import logging
import os

import discord
from discord_py_utilities.messages import send_message, send_response

from classes.access import AccessControl
from database.transactions.BanTransactions import BanTransactions
from view.base.secureview import SecureView
from view.modals.inputmodal import send_modal


class ReportButtons(SecureView) :
	"""Two way communication between the reporting user and the banwatch staff.

	The report itself is posted in the staff channel, staff respond with the button which DMs the
	reporter. That DM carries the same view, allowing the reporter to respond back to the staff
	channel. The ban id in the embed footer is what keeps the conversation routed.
	"""
	bot = None

	def __init__(self) :
		super().__init__(timeout=None)
		self.user = None
		self.guild = None
		self.ban = None
		self.ban_id = None
		self.dmChannel = False

	# ============================================================
	@discord.ui.button(label="Respond", style=discord.ButtonStyle.success, custom_id="Respond_report")
	async def respond(self, interaction: discord.Interaction, button: discord.ui.Button) :
		if not await self.load_data(interaction) :
			return await send_response(interaction, "This report is no longer available; the ban record is gone.",
			                           ephemeral=True)
		if self.user is None :
			return await send_response(interaction, "The user of this report could not be found.", ephemeral=True)
		if not await self.check_perms(interaction) :
			return
		target = "the banwatch staff" if self.dmChannel else self.user.name
		message = await send_modal(interaction, f"Your response has been delivered to {target}.",
		                           "What's your message?", 2000, ephemeral=False)
		if not message :
			return
		await self.send_embed(interaction, message)

	# ============================================================
	async def check_perms(self, interaction: discord.Interaction) -> bool :
		"""In DMs only the reporter may respond, in the staff channel only banwatch staff."""
		if self.dmChannel :
			if interaction.user.id != self.user.id :
				await send_response(interaction, "You can only respond to your own report.", ephemeral=True)
				return False
			return True
		if not AccessControl().access_all(interaction.user.id) :
			await send_response(interaction, "You don't have permission to do that!", ephemeral=True)
			return False
		return True

	# ============================================================
	async def send_embed(self, interaction: discord.Interaction, content) :
		embed = discord.Embed(title=self.create_title(interaction), color=discord.Color.blurple(),
		                      description=content)
		embed.set_footer(text=self.ban_id)
		if self.dmChannel :
			staff_channel = self.bot.get_channel(int(os.getenv("BANS")))
			if staff_channel is None :
				return await send_message(interaction.channel,
				                          "Unable to deliver your response, please contact the banwatch staff directly.")
			await send_message(staff_channel, " ", embed=embed, view=ReportButtons())
			return
		try :
			await send_message(self.user, " ", embed=embed, view=ReportButtons())
		except Exception as e :
			logging.warning(f"Failed to deliver report response to {self.user.id}: {e}")
			await send_message(interaction.channel,
			                   f"Unable to send message to {self.user.name}, their DMs are closed.")

	# ============================================================
	def create_title(self, interaction: discord.Interaction) :
		"""Staff stay anonymous towards the reporter, the reporter does not towards staff."""
		if self.dmChannel :
			return f"Response from {interaction.user.name} for report: {self.ban_id}"
		return f"Response from the banwatch staff for report: {self.ban_id}"

	# ============================================================
	async def load_data(self, interaction: discord.Interaction) -> bool :
		self.bot = interaction.client
		self.dmChannel = isinstance(interaction.channel, discord.DMChannel)
		self.ban_id = int(interaction.message.embeds[0].footer.text)
		self.ban = BanTransactions().get(self.ban_id, override=True)
		if self.ban is None :
			return False
		self.guild = self.bot.get_guild(self.ban.gid)
		self.user = self.bot.get_user(self.ban.uid)
		if self.user is None :
			try :
				self.user = await self.bot.fetch_user(self.ban.uid)
			except discord.errors.NotFound :
				self.user = None
		return True
