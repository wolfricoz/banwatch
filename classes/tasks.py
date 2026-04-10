import asyncio
import os

import discord
from discord_py_utilities.messages import send_message

from classes.queue import queue
from database.current import Bans
from database.transactions.BanTransactions import BanTransactions
from view.buttons.banapproval import BanApproval


async def pending_bans(bot, revoked=False, limit = None) :
	bans = BanTransactions().get_all_pending()
	channel = bot.get_channel(bot.BANCHANNEL)
	ban: Bans
	found_bans = []
	if revoked :
		await send_message(channel, "fetching pending bans after revoking ban")
	count = 0

	for ban in bans :
		if limit and count >= limit :
			break
		if count % 10 == 0:
			await asyncio.sleep(0)
		if ban.approved is True or ban.hidden is True :
			continue
		count += 1
		reason = ban.reason
		wait_id = ban.ban_id
		user_id = ban.uid
		guild_id = ban.gid
		user = bot.get_user(user_id)
		guild = bot.get_guild(guild_id)
		proof_count = len(ban.proof)

		# If the user is not found in the cache, fetch from the API
		if user is None :
			try :
				user = await bot.fetch_user(user_id)
			except discord.NotFound :
				print(f"User with ID {user_id} not found.")
			except discord.HTTPException as e :
				print(f"Failed to fetch user with ID {user_id}: {e}")

		# If the guild is not found in the cache, fetch from the API
		if guild is None :
			print(f"Guild with ID {guild_id} not found in cache.")
			try :
				guild = await bot.fetch_guild(guild_id)
			except discord.NotFound :
				print(f"Guild with ID {guild_id} not found.")
			except discord.HTTPException as e :
				print(f"Failed to fetch guild with ID {guild_id}: {e}")

		if user is None or guild is None or reason is None :
			print(f"Error: {user} {guild} {reason}")
			continue
		found_bans.append(ban)
		try :
			embed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({guild.owner})",
			                      description=f"{reason}")
			embed.add_field(name="Staff Member", value=ban.staff, inline=False)
			if ban.edited:
				embed.add_field(name=f"Edited by {ban.edited_by}", value=ban.edited.strftime('%m/%d/%Y'), inline=False)
			if proof_count > 0 :
				embed.add_field(name="Evidence attached", value=f"{proof_count} piece{'s' if proof_count > 1 else ''} of evidence attached", inline=False)

			embed.set_footer(text=f"/approve_ban {wait_id}")
			queue().add(channel.send(f"", embed=embed, view=BanApproval(bot, wait_id, True)),
			            priority=2)
		except Exception as e :
			print(f"Error: {e}")
	if len(found_bans) < 1 :
		await send_message(channel, f"No pending bans, good job team!", error_mode='ignore')
		return
	await send_message(channel, f"Heres the pending bans <@&{os.getenv('STAFF_ROLE')}>!", error_mode='warn')
