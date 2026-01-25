from sqlalchemy import Select

from database.current import BanMessages
from database.transactions.DatabaseController import DatabaseTransactions


class BanMessageTransactions(DatabaseTransactions):
    def get_by_ban_id(self, ban_id: int) -> str:
        with self.createsession() as session:
            return session.scalars(Select(BanMessages).where(BanMessages.ban_id == ban_id)).all()

    def add_ban_message(self, ban_id: int, guild_id: int, message_id: int) -> None:
        with self.createsession() as session:\
            # Prevent duplicate entries
            existing = session.scalar(
                Select(BanMessages).where(
                    BanMessages.message_id == message_id
                )
            )
            if existing is not None:
                return

            ban_message = BanMessages(
                ban_id=ban_id,
                server_id=guild_id,
                message_id=message_id
            )
            session.add(ban_message)
            self.commit(session)

    def delete_bm(self, message_id: int) -> None:
        with self.createsession() as session:
            bm = session.scalar(
                Select(BanMessages).where(BanMessages.message_id == message_id)
            )
            if bm:
                session.delete(bm)
                self.commit(session)