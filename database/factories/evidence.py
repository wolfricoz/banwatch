import random

from database.databaseController import BanDbTransactions, ProofDbTransactions
from database.factories.ban import BanFactory
from database.factories.serverfactory import ServerFactory


class EvidenceFactory :
	def create(self, amount = 1,  ban = None):
		records = []
		if not ban:
			ban = BanFactory().create()

		if amount == 1:
			return ProofDbTransactions().add(ban.ban_id, ban.uid, "This user was troublesome",["https://google.com/", "https://youtube.com/"] )
		while len(records) <= amount:
			records.append(ProofDbTransactions().add(ban.ban_id, ban.uid, "This user was troublesome",["https://google.com/", "https://youtube.com/"] ))
		return records