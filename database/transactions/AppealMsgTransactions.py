
from sqlalchemy.orm import Mapped

from database.current import AppealMsgs, Appeals
from database.transactions.DatabaseController import DatabaseTransactions


class AppealMsgTransactions(DatabaseTransactions) :


	def add(self, message: str, sender: int, recipient: int, appeal: int | Mapped[int] | Appeals) :
		with DatabaseTransactions().createsession() as session :
			if isinstance(appeal, Appeals) :
				appeal = appeal.id
			msg = AppealMsgs(message=message, sender=sender, recipient=recipient, appeal_id=appeal)
			session.add(msg)
			DatabaseTransactions().commit(session)
			return msg

	def get_chat_log(self, appeal: int | Appeals) :
		with self.createsession() as session :

			return session.query(AppealMsgs).where(AppealMsgs.appeal_id == appeal.id).order_by(AppealMsgs.created).all()
