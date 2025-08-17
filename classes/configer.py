"""This class generates the config file, with functions to change and get values from it"""
import json
import logging
import os
from abc import ABC, abstractmethod

appeals_path = "settings/appeals.json"
config_path = "settings/config.json"


class Configer(ABC) :
	"""This class generates the config file, with functions to change and get values from it"""

	@staticmethod
	@abstractmethod
	async def create(guildid, guildname) :
		"""Creates the config"""
		return
		# print("updating config")
		# path = f"configs/{guildid}.json"
		# config = {}
		# if not os.path.isdir('configs'):
		#     os.mkdir('configs')
		# if os.path.exists(path):
		#     with open(path, 'r') as f:
		#         config = json.load(f)
		# dictionary = {
		#     "name"      : config.get("name", guildname),
		#     "modchannel": config.get("modchannel", 0),
		#     "allow_appeals": config.get("allow_appeals", True)
		# }
		# json_object = json.dumps(dictionary, indent=4)
		# with open(f"configs/{guildid}.json", "w") as outfile:
		#     outfile.write(json_object)
		# logging.info(f"config created for {guildid}")

	@staticmethod
	@abstractmethod
	async def create_bot_config() :
		"""Creates the general config"""
		if not os.path.isdir("settings") :
			os.mkdir("settings")
		dictionary = {
			"blacklist" : [],
			"checklist" : [

			],
		}
		json_object = json.dumps(dictionary, indent=4)
		if os.path.exists(config_path) :
			with open(config_path) as f :
				data = json.load(f)
				dictionary = {
					"user_blacklist" : data.get("user_blacklist", []),
					"blacklist"      : data.get("blacklist", []),
					"checklist"      : data.get("checklist", [])
				}
			with open(config_path, "w") as f :
				json.dump(dictionary, f, indent=4)
			return
		with open(config_path, "w") as outfile :
			outfile.write(json_object)
			logging.info(f"universal config created")

	@staticmethod
	@abstractmethod
	async def create_appeals() :
		"""Creates the general config"""
		dictionary = {

		}
		json_object = json.dumps(dictionary, indent=4)
		if not os.path.isdir('settings') :
			os.mkdir('settings')
		if os.path.exists(appeals_path) :
			return
		with open(appeals_path, "w") as outfile :
			outfile.write(json_object)
			logging.info(f"universal appeals created")

	@staticmethod
	@abstractmethod
	async def add_appeal(userid, guildid, reason) :
		"""This adds an appeal to the appeals.json file"""
		if not os.path.exists(appeals_path) :
			await Configer.create_appeals()
		with open(appeals_path) as f :
			data = json.load(f)
			data[f"{userid}"] = {}
			data[f"{userid}"][f"{guildid}"] = {}
			data[f"{userid}"][f"{guildid}"]["reason"] = str(reason)
			data[f"{userid}"][f"{guildid}"]["status"] = "pending"

		with open(appeals_path, 'w') as f :
			json.dump(data, f, indent=4)
			logging.info(f"{guildid} added to appeals")

	# appeals start here
	@staticmethod
	@abstractmethod
	async def get_all_appeals() :
		"""Gets the appeals from the appeals.json file"""
		if os.path.exists(appeals_path) :
			with open(appeals_path) as f :
				data = json.load(f)
				return data

	@staticmethod
	@abstractmethod
	async def get_user_appeals(userid) :
		"""Gets the appeals from the appeals.json file"""
		if not os.path.exists(appeals_path) :
			await Configer.create_appeals()
		with open(appeals_path) as f :
			data = json.load(f)
			if str(userid) not in data.keys() :
				return None
			return data[str(userid)]

	@staticmethod
	@abstractmethod
	async def update_appeal_status(userid, guildid, status) :
		"""Changes the status of an appeal"""
		if status not in ["pending", "approved", "denied"] :
			return
		if not os.path.exists(appeals_path) :
			await Configer.create_appeals()
		with open(appeals_path) as f :
			data = json.load(f)
			print(userid, " ", guildid, " ", status)
			data[str(userid)][str(guildid)]["status"] = str(status)
		with open(appeals_path, 'w') as f :
			json.dump(data, f, indent=4)
			logging.info(f"{guildid} changed to {status}")

	# config editing starts hee
	@staticmethod
	@abstractmethod
	async def change(guildid, interaction, value, key) :
		"""Changes value in the config"""
		if os.path.exists(f"configs/{guildid}.json") :
			with open(f"configs/{guildid}.json") as f :
				data = json.load(f)
				data[key] = value
			with open(f"configs/{guildid}.json", 'w') as f :
				json.dump(data, f.name, indent=4)
			await interaction.followup.send(f"Config key **{key}** changed to **{value}**")

	async def get(guildid, key) :
		"""Gets a value from the config"""
		if os.path.exists(f"configs/{guildid}.json") :
			with open(f"configs/{guildid}.json") as f :
				data = json.load(f)
				return data.get(key, None)

	# blacklist starts here
	@staticmethod
	@abstractmethod
	async def add_to_blacklist(guildid) :
		"""Adds a server to the blacklist"""
		if os.path.exists(config_path) :
			with open(config_path) as f :
				data = json.load(f)
				data["blacklist"].append(guildid)
			with open(config_path, 'w') as f :
				json.dump(data, f, indent=4)
				logging.info(f"{guildid} added to blacklist")
		else :
			logging.warning("No blacklist found")

	@staticmethod
	@abstractmethod
	async def remove_from_blacklist(guildid) :
		"""Removes a server from the blacklist"""
		if os.path.exists(config_path) :
			with open(config_path) as f :
				data = json.load(f)
				data["blacklist"].remove(guildid)
			with open(config_path, 'w') as f :
				json.dump(data, f, indent=4)
				logging.info(f"{guildid} removed from blacklist")
		else :
			logging.warning("No blacklist found")

	@staticmethod
	@abstractmethod
	async def is_blacklisted(guildid) :
		"""Checks if a server is blacklisted"""
		if os.path.exists(config_path) :
			with open(config_path) as f :
				data = json.load(f)
				if guildid in data["blacklist"] :
					return True

	# user blacklist starts here
	@staticmethod
	@abstractmethod
	async def add_to_user_blacklist(userid) :
		"""Adds a user to the user blacklist"""
		if os.path.exists(config_path) :
			with open(config_path) as f :
				data = json.load(f)
				data["user_blacklist"].append(userid)
			with open(config_path, 'w') as f :
				json.dump(data, f, indent=4)
				logging.info(f"{userid} added to user blacklist")
		else :
			logging.warning("No blacklist found")

	@staticmethod
	@abstractmethod
	async def remove_from_user_blacklist(userid) :
		"""Removes a user from the user blacklist"""
		if os.path.exists(config_path) :
			with open(config_path) as f :
				data = json.load(f)
				data["user_blacklist"].remove(userid)
			with open(config_path, 'w') as f :
				json.dump(data, f, indent=4)
				logging.info(f"{userid} removed from user blacklist")
		else :
			logging.warning("No blacklist found")

	@staticmethod
	@abstractmethod
	async def is_user_blacklisted(userid) :
		"""Checks if a user is blacklisted"""
		if not os.path.exists(config_path) :
			logging.warning("No blacklist file does not exist")
			return False
		with open(config_path) as f :
			data = json.load(f)
			if userid in data.get("user_blacklist", []) :
				return True

		return False

	# Checklist starts here
	@staticmethod
	@abstractmethod
	async def add_checklist(word: str) :
		"""Adds a word to the checklist"""
		if os.path.exists(config_path) :
			with open(config_path) as f :
				data = json.load(f)
				if word in data["checklist"] :
					return
				data["checklist"].append(word)
			with open(config_path, 'w') as f :
				json.dump(data, f, indent=4)
				logging.info(f"{word} added to checklist")
		else :
			await Configer.create_bot_config()

	@staticmethod
	@abstractmethod
	async def remove_checklist(word: str) :
		"""Removes a word from the checklist"""
		if os.path.exists(config_path) :
			with open(config_path) as f :
				data = json.load(f)
				data["checklist"].remove(word)
			with open(config_path, 'w') as f :
				json.dump(data, f, indent=4)
				logging.info(f"{word} removed from checklist")
		else :
			await Configer.create_bot_config()

	@staticmethod
	@abstractmethod
	async def get_checklist() :
		"""Gets the checklist"""
		if os.path.exists(config_path) :
			with open(config_path) as f :
				data = json.load(f)
				return data["checklist"]
