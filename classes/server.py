import logging

from database.transactions.BanTransactions import BanTransactions
from database.transactions.ServerTransactions import ServerTransactions


class Server :
	def __init__(self, guild_id: int) :
		self.guild_id = guild_id
		self.banned_ids = set(self.get_banned_ids(guild_id))

		# Performance/Accuracy Fix: Using a set prevents O(N^2) lookups
		# and isolates tracking to this instance alone.
		self.checked_ids = set()

	def get_banned_ids(self, guild_id: int) -> list[int]  :
		"""

		:return:
		:param guild_id:
		:return:
		"""
		return ServerTransactions().get_bans(guild_id, uid_only=True)

	def check_ban(self, user_id: int) -> bool :
		if user_id in self.banned_ids :
			self.checked_ids.add(user_id)
			return True
		return False

	def add_checked_id(self, user_id: int) -> None :
		self.checked_ids.add(user_id)

	def check_missed_ids(self) -> list[int] :
		missed_ids = []
		for user_id in self.banned_ids :
			if user_id not in self.checked_ids :
				missed_ids.append(user_id)
		return missed_ids

	def remove_missing_ids(self, missing_ids: list[int]) -> int :
		"""Soft-removes bans that are in our database but no longer on the guild.

		This writes directly rather than going through queue(). The reconciliation runs inside
		check_guild_bans, which is itself awaited inside a queued Bans().update() - so anything
		queued from here would sit unprocessed until the entire multi-guild sweep finished, and
		would be dropped outright if the queue were cleared or the bot restarted first.

		:return: number of bans actually removed.
		"""
		if not missing_ids :
			return 0
		ban_ids = [user_id + self.guild_id for user_id in missing_ids]
		removed = BanTransactions().delete_soft_bulk(ban_ids)
		if removed != len(ban_ids) :
			logging.warning(
				f"Soft-removed {removed}/{len(ban_ids)} missing bans in {self.guild_id}; "
				f"{len(ban_ids) - removed} were already removed or could not be found.")
		else :
			logging.info(f"Soft-removed {removed} missing bans in {self.guild_id}")
		return removed