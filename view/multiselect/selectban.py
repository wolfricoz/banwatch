import logging

import discord.ui
from discord_py_utilities.bans import ban_member
from discord_py_utilities.messages import send_message, send_response

from classes.bans import Bans
from database.databaseController import BanDbTransactions
from view.buttons.confirm import Confirm


class SelectBan(discord.ui.View):

	"""This class is for the select menu, which is used to select a user to ban."""

	def __init__(self, user_id):
		super().__init__(timeout=None)
		self.bans = BanDbTransactions().get_all_user(user_id)

		options = [discord.SelectOption(
				label=f"{ban.guild.name} - {ban.uid}",
					value=str(ban.ban_id),
					emoji="🔨",
				) for ban
					in self.bans]
		select = 	discord.ui.Select(
				placeholder="Select the ban for cross-banning",
				options=options,

			)

		select.callback = self.select_ban
		self.add_item(select)


	async def select_ban(self, interaction: discord.Interaction):
		"""This function is called when the user selects a ban from the select menu."""
		ban_id = int(self.children[0].values[0])
		ban = BanDbTransactions().get(ban_id)
		result = await Confirm().send_confirm(interaction, message=f'Are you sure you want to cross-ban this user with the ban from {ban.guild.name}?')
		if not result:
			await send_response(interaction, "Cancelled", ephemeral=True)
			return
		user = interaction.client.get_user(int(ban.uid))
		if user is None:
			user = await interaction.client.fetch_user(int(ban.uid))

		reason = f"Cross-ban from {ban.guild.name} with ban id: {ban_id}"
		await ban_member(Bans(), interaction, user, reason, days=0)
		await send_message(interaction.channel, f"Banning {user.mention} with reason: {reason}")


	async def on_timeout(self) -> None:
		"""This function is called when the view times out."""
		return
