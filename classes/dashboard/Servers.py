import base64
import logging
import os

import discord

from database.current import Servers as dbServers
import requests
from discord.ext import commands

class Servers:
	ip_address = os.getenv('DASHBOARD_URL')
	key = os.getenv('DASHBOARD_KEY')
	secret = os.getenv('DASHBOARD_SECRET')


	async def update_server(self, bot: commands.Bot, guild: dbServers):
		path = "/api/server/create"
		url = f"{self.ip_address}{path}"
		encoded = base64.b64encode(f"{self.key}:{self.secret}".encode('ascii'))

		headers = {
			"Authorization": f"Bearer {encoded}",
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
		result = requests.post(url, headers=headers, json=data)
		if result.status_code != 200:
			logging.info(f"Server {guild.id} could not be updated: {result.status_code}")
		logging.info(f"Server {guild.id} updated")

