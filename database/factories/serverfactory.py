import random

from database.databaseController import BanDbTransactions, ServerDbTransactions


class ServerFactory :
	def create(self, amount = 1):
		records = []

		if amount == 1:
			return ServerDbTransactions().add(random.randrange(10**17, 10**18), "owner", "server_name", 100, "invite")
		while len(records) <= amount:
			records.append(ServerDbTransactions().add(random.randrange(10**17, 10**18), "owner", "server_name", 100, "invite"))
		return records