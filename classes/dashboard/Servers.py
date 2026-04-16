import asyncio
import base64
import logging
import os

import aiohttp

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
		self.encoded = base64.b64encode(f"{self.key}:{self.secret}".encode('ascii')).decode() # Legacy, not used anymore but keeping in case we need it for something else later

	async def update_servers(self, guilds: list[dbServers]) :
		headers = {
			"Authorization" : f"Bearer {self.key}",
			"Content-Type"  : "application/json",
			"Accept" : "application/json"
		}

		if not guilds :
			return None

		# Prepare the payload
		data = [{
			"id"           : guild.id,
			"banwatch"     : guild.active,
			"name"         : guild.name,
			"owner"        : guild.owner,
			"owner_id"     : guild.owner_id,
			"member_count" : guild.member_count,
			"invite"       : guild.invite
		} for guild in guilds]

		try :
			# 'async with' ensures the connection closes properly even if it fails
			async with aiohttp.ClientSession() as session :
				async with session.post(
						self.url,
						headers=headers,
						json={"servers" : data},
						timeout=aiohttp.ClientTimeout(total=5)  # 5s total timeout
				) as response :

					if response.status != 200 :
						error_text = await response.text()
						logging.info(f"Server group update failed: {response.status}: {error_text}")
						return None

					# 'await' here is key! It yields control back to the loop
					results = await response.json()

					for res in results :
						server_id = res.get('id', 0)
						if server_id == 0 :
							continue

						# Offload the DB update to a thread if it's a blocking DB call
						await asyncio.to_thread(
							ServerTransactions().update,
							server_id,
							premium=res.get('premium')
						)

						logging.info(f"Server {server_id} updated: {res}")

					logging.info(f"{len(guilds)} Servers updated successfully.")

		except aiohttp.ClientConnectorError :
			logging.warning("Could not connect to the API server. Is it running?")
		except asyncio.TimeoutError :
			logging.warning("The API request timed out.")
		except Exception as e :
			logging.error(f"Error updating servers: {e}", exc_info=True)


