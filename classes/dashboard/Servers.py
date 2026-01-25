import base64
import logging
import os

import requests
from discord.ext import commands

from database.current import Servers as dbServers
from database.transactions.ServerTransactions import ServerTransactions


class Servers:
	ip_address = os.getenv('DASHBOARD_URL')
	key = os.getenv('DASHBOARD_KEY')
	secret = os.getenv('DASHBOARD_SECRET')
	skip = False
	def __init__(self):
		self.path = "/api/server/create"
		self.url = f"{self.ip_address}{self.path}"
		self.encoded = base64.b64encode(f"{self.key}:{self.secret}".encode('ascii')).decode()



	async def update_servers(self, guilds: list[dbServers]):

		headers = {
			"Authorization": f"Basic {self.encoded}",
			"Content-Type": "application/json"
		}
		logging.info(f"headers: {headers}")
		if guilds is None:
			return None

		data = [{
			"id": guild.id,
			"banwatch": guild.active,
			"name": guild.name,
			"owner": guild.owner,
			"owner_id": guild.owner_id,
			"member_count": guild.member_count,
			"invite": guild.invite
		} for guild in guilds]
		try:
			result = requests.post(self.url, headers=headers, json={"servers": data}, timeout=5)
			if result.status_code != 200:
				logging.info(
					f"server group {[g.id for g in guilds]} could not be updated: {result.status_code}: {result.text}")
				print(
					f"server group {[g.id for g in guilds]} could not be updated: {result.status_code}: {result.text}")
				# logging.info(f"Variables:\npath: {path}\nurl: {url}\nheaders: {headers}, key: {self.key}\nsecret: {self.secret}")
				return None

			results = result.json()
			for result in results:
				server_id = result.get('id', 0)
				if server_id == 0:
					logging.info("No server id returned, skipping")
					continue
				ServerTransactions().update(server_id, premium=result.get('premium', None))

				logging.info(f"Server {server_id} updated successfully: {result}")
				print(f"Server {server_id} updated successfully: {result}")
			logging.info(f"{len(guilds)} Servers updated")
		except Exception as e:
			logging.warning(f"Error updating server {[g.id for g in guilds]}: {e}", exc_info=True)


