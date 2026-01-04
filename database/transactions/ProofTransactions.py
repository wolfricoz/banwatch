import json
import logging

from sqlalchemy import Select
from sqlalchemy.util import to_list

from database.current import Bans, Proof
from database.transactions.BanReasonTransactions import DatabaseTransactions


class ProofDbTransactions(DatabaseTransactions) :

	def exists(self, ban_id: int) :
		return session.scalar(Select(Proof).where(Proof.ban_id == ban_id))

	def add(self, ban_id: int, user_id: int, proof: str, attachments: list[str]) -> Proof | bool :
		logging.info(f"Adding proof for {ban_id} with {proof} and {len(attachments)} attachments")
		proof = Proof(ban_id=ban_id, uid=user_id, proof=proof, attachments=json.dumps(attachments))
		session.add(proof)
		self.commit(session)
		return proof

	def get(self, ban_id: str | int = None, user_id: int = None) -> list | None :
		if isinstance(ban_id, str) :
			ban_id = int(ban_id)
		if user_id :
			return to_list(session.scalars(Select(Proof).join(Bans).where(Proof.uid == user_id)).all())
		return to_list(session.scalars(Select(Proof).join(Bans).where(Proof.ban_id == ban_id)).all())

	def delete(self, id: int) -> bool :
		entry: Proof = session.scalar(Select(Proof).where(Proof.id == id))
		if entry is None :
			return False
		logging.info(f"Deleting evidence {id} from {entry.ban_id}")
		if not entry :
			return False
		session.delete(entry)
		self.commit(session)
		return True
