import random

from database.databaseController import BanDbTransactions
from database.factories.guild import ServerFactory


class BanFactory :
	def create(self, amount = 1, guild = None, approved = True):
		records = []
		if not guild:
			guild = ServerFactory().create()
		if amount == 1:
			return BanDbTransactions().add(random.randrange(10**17, 10**18), guild.id, "reason", "staff", approved=approved)
		while len(records) < amount:
			records.append(BanDbTransactions().add(random.randrange(10**17, 10**18), guild.id, "reason", "staff", approved=approved))
		return records