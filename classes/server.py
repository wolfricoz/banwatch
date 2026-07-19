import logging

from sqlalchemy import ColumnElement

from classes.queue import queue
from database.current import Bans
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

	# FIX: Changed to regular 'def' because it just pushes tasks to the queue
	def remove_missing_ids(self, missing_ids: list[int]) -> None :
		for user_id in missing_ids :
			queue().add(self.soft_delete(user_id))

	async def soft_delete(self, user_id: int) -> None :
		logging.info(f"Soft removing missing ban for {user_id} in {self.guild_id}")
		BanTransactions().delete_soft(user_id + self.guild_id)