import logging
import os
from typing import T

import discord
from discord import app_commands

from classes.blacklist import blacklist_check
from classes.configer import Configer
from classes.singleton import Singleton
from database.databaseController import StaffDbTransactions


class AccessControl(metaclass=Singleton) :
	staff: dict = {

	}

	def __init__(self) :
		self.add_staff_to_dict()

	def reload(self) :
		self.add_staff_to_dict()

	def add_staff_to_dict(self) :
		self.staff = {}
		staff_members = StaffDbTransactions().get_all()
		for staff in staff_members :
			role = staff.role.lower()
			if role in self.staff :
				self.staff[role].append(staff.uid)
				continue
			self.staff[role] = [staff.uid]
		logging.info("Staff information has been reloaded:")
		logging.info(self.staff)

	def access_owner(self, user) -> bool :
		return True if user.id == int(os.getenv('OWNER')) else False

	def access_all(self, user) -> bool :
		return True if user.id in self.staff.get('dev', []) or user.id in self.staff.get('rep', []) else False

	def access_dev(self, user) -> bool :
		return True if user.id in self.staff.get('dev', []) else False

	def check_access(self, role="") -> T :
		def pred(interaction: discord.Interaction) -> bool:
			match role.lower() :
				case "owner" :
					return self.access_owner(interaction.user)
				case "dev" :
					return self.access_dev(interaction.user)
				case _ :
					return self.access_all(interaction.user)
		return app_commands.check(pred)

	def check_blacklist(self):
		async def pred(interaction: discord.Interaction) -> bool:
			if await Configer.is_user_blacklisted(interaction.user.id):
				return False
			return True

		return app_commands.check(pred)