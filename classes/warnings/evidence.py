import discord

from database.transactions.WarningTransactions import WarningTransactions


class WarningEvidence():

	def __init__(self, warning: Warning | int):
		if isinstance(warning, int):
			self.warning = WarningTransactions().get_id(warning)
		else :
			self.warning = warning



	async def create_evidence(self, message: discord.Message):





