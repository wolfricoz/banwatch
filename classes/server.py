from database.databaseController import ServerDbTransactions


class Server():
    banned_ids = []
    checked_ids = []

    def __init__(self, guild_id: int):
        self.banned_ids = self.get_banned_ids(guild_id)

    def get_banned_ids(self, guild_id: int) -> list[int]:
        return ServerDbTransactions().get_bans(guild_id, uid_only=True)

    def check_ban(self, user_id: int) -> bool:
        if user_id in self.banned_ids:
            self.checked_ids.append(user_id)
            return True
        return False

