from sqlalchemy.testing.plugin.plugin_base import logging

from database.databaseController import ServerDbTransactions, BanDbTransactions


class Server():
    banned_ids = []
    checked_ids = []
    guild_id = 0

    def __init__(self, guild_id: int):
        self.banned_ids = self.get_banned_ids(guild_id)
        self.guild_id = guild_id

    def get_banned_ids(self, guild_id: int) -> list[int]:
        return ServerDbTransactions().get_bans(guild_id, uid_only=True)

    def check_ban(self, user_id: int) -> bool:
        if user_id in self.banned_ids:
            self.checked_ids.append(user_id)
            return True
        return False

    def add_checked_id(self, user_id: int) -> None:
        self.checked_ids.append(user_id)

    def check_missed_ids(self) -> list[int]:
        missed_ids = []
        for user_id in self.banned_ids:
            if user_id not in self.checked_ids:
                missed_ids.append(user_id)
        return missed_ids

    def remove_missing_ids(self) -> None:
        for user_id in self.check_missed_ids():
            logging.info(f"Soft removing missing ban for {user_id} in {self.guild_id}")
            BanDbTransactions().delete_soft(user_id + self.guild_id)