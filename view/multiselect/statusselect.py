import logging

import discord.ui
from discord_py_utilities.messages import send_response

from database.transactions.AppealsTransactions import AppealsDbTransactions
from database.transactions.BanTransactions import BanTransactions
from view.base.secureview import SecureView


class StatusSelect(discord.ui.Select) :
	def __init__(self, status, ban_id) :
		self.ban_id = ban_id
		options = [
			discord.SelectOption(
				label=s.get('reason', "Custom")[:99],
				value=s.get('value', "custom")[:99],
				description=s.get('description', "")[:99],
				emoji=s.get('emote')
			)
			for s in status
		]

		super().__init__(
			placeholder="Select your ban reason here!",
			options=options,
			min_values=1,
			max_values=1
		)

	async def callback(self, interaction: discord.Interaction) :
		selected_value = self.values[0]
		AppealsDbTransactions().change_status(self.ban_id, selected_value)
		ban = BanTransactions().get(self.ban_id)
		await send_response(interaction, f"Appeal status for {self.ban_id} updated to `{selected_value}`")

		try:
			user = interaction.client.get_user(ban.uid)
			if selected_value == "approved" :
				await interaction.guild.unban(user)
			await user.send(f"Your appeal has been updated to `{selected_value}`")
		except Exception as e:
			logging.error(f"Failed to send appeal update to {ban.uid}: {e}", exc_info=True)


class SelectStatus(SecureView) :
	def __init__(self, ban_id) :
		super().__init__(timeout=None)
		self.status = [
			{
				"reason"      : "Approved",
				"description" : "Unbans user",
				"value"       : "approved",
				"emote"       : "✅"
			},
			{
				"reason"      : "Denied",
				"description" : "Denies appeal",
				"value"       : "denied",
				"emote"       : "❌"
			},
			# {
			# 	"reason"      : "Pending",
			# 	"description" : "Awaiting review",
			# 	"value"       : "pending",
			# 	"emote"       : "⏳"
			# }
		]

		self.add_item(StatusSelect(self.status, ban_id))
