from database.transactions.ProofTransactions import ProofTransactions
from database.factories.ban import BanFactory


class EvidenceFactory :
	def create(self, amount = 1,  ban = None):
		records = []
		if not ban:
			ban = BanFactory().create()

		if amount == 1:
			return ProofTransactions().add(ban.ban_id, ban.uid, "This user was troublesome", ["https://google.com/", "https://youtube.com/"])
		while len(records) <= amount:
			records.append(ProofTransactions().add(ban.ban_id, ban.uid, "This user was troublesome", ["https://google.com/", "https://youtube.com/"]))
		return records