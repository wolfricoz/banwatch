import logging
import os

import discord
from discord import app_commands


from classes.configer import Configer
from classes.singleton import Singleton
from database.transactions.StaffTransactions import StaffTransactions
from database.transactions.ServerTransactions import ServerTransactions


class AccessControl(metaclass=Singleton) :
	staff: dict = {

	}
	premium: list = []

	def __init__(self) :
		self.add_staff_to_dict()
		self.add_premium_to_dict()
		print(self.premium)

	def reload(self) :
		self.add_staff_to_dict()
		self.add_premium_to_dict()

	def add_staff_to_dict(self) :
		self.staff = {}
		staff_members = StaffTransactions().get_all()
		for staff in staff_members :
			role = staff.role.lower()
			if role in self.staff :
				self.staff[role].append(staff.uid)
				continue
			self.staff[role] = [staff.uid]
		logging.info("Staff information has been reloaded:")
		logging.info(self.staff)

	def add_premium_to_dict(self) :
		self.premium = ServerTransactions().get_premium_ids()

	def reload_premium(self) :
		self.add_premium_to_dict()

	def access_owner(self, user_id: int) -> bool :
		return True if user_id == int(os.getenv('OWNER')) else False

	def access_all(self, user_id: int) -> bool :
		return True if user_id in self.staff.get('DevTools', []) or user_id in self.staff.get('rep', []) else False

	def access_dev(self, user_id: int) -> bool :
		return True if user_id in self.staff.get('DevTools', []) else False

	def check_access(self, role="") :
		def pred(interaction: discord.Interaction) -> bool:
			match role.lower() :
				case "owner" :
					return self.access_owner(interaction.user.id)
				case "DevTools" :
					return self.access_dev(interaction.user.id)
				case _ :
					return self.access_all(interaction.user.id)
		return app_commands.check(pred)

	def check_blacklist(self):
		async def pred(interaction: discord.Interaction) -> bool:
			if await Configer.is_user_blacklisted(interaction.user.id):
				return False
			return True

		return app_commands.check(pred)

	def check_premium(self):
		async def pred(interaction: discord.Interaction) -> bool:
			result = self.is_premium(interaction.guild.id)
			if not result :
				await interaction.response.send_message(
					"This command is premium only",
					ephemeral=True
				)
			return result

		return app_commands.check(pred)

	def is_premium(self, guild_id: int) -> bool :
		"""Check if a guild has premium access."""
		return guild_id in self.premium