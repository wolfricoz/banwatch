import base64
import logging
import os

import discord

from database.current import Servers as dbServers
import requests
from discord.ext import commands

from database.transactions.ServerTransactions import ServerTransactions


class Servers:
	ip_address = os.getenv('DASHBOARD_URL')
	key = os.getenv('DASHBOARD_KEY')
	secret = os.getenv('DASHBOARD_SECRET')
	skip = False


	async def update_server(self, bot: commands.Bot, guild: dbServers):
		if self.skip:
			logging.warning(f"Skipping {guild.name} ({guild.id}) update due to previous connection error")
			return
			return
		path = "/api/server/create"
		url = f"{self.ip_address}{path}"
		encoded = base64.b64encode(f"{self.key}:{self.secret}".encode('ascii')).decode()

		headers = {
			"Authorization": f"Basic {encoded}",
			"Content-Type": "application/json"
		}

		discord_guild = bot.get_guild(guild.id)
		data = {
			"id": guild.id,
			"banwatch": guild.active,
			"name": guild.name,
			"owner": guild.owner,
			"owner_id": discord_guild.owner.id,
			"member_count": guild.member_count,
			"invite": guild.invite
		}

		try:

			result = requests.post(url, headers=headers, json=data, timeout=5)
		except requests.exceptions.ConnectionError:
			self.skip = True
			logging.info(f"Server {guild.id} could not be updated: Connection error")
			return
		if result.status_code != 200:
			logging.info(f"Server {guild.id} could not be updated: {result.status_code}")
			return
		result = result.json()
		logging.info(f"Server {guild.id} updated: {result}")
		ServerTransactions().update(discord_guild.id, discord_guild.owner.name, discord_guild.name, len(discord_guild.members), guild.invite, owner_id=discord_guild.owner_id, premium=result.get('premium', None))
		logging.info(f"Server {guild.id} updated to {result.get('premium', True)}")
		logging.info(f"Server {guild.id} updated")

