import asyncio
import logging
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
				logging.warning(f"Pending ban: user {user_id} not found.")
			except discord.HTTPException as e :
				logging.warning(f"Pending ban: failed to fetch user {user_id}: {e}")

		# If the guild is not found in the cache, fetch from the API
		if guild is None :
			logging.debug(f"Pending ban: guild {guild_id} not in cache, fetching.")
			try :
				guild = await bot.fetch_guild(guild_id)
			except discord.NotFound :
				logging.warning(f"Pending ban: guild {guild_id} not found.")
			except discord.HTTPException as e :
				logging.warning(f"Pending ban: failed to fetch guild {guild_id}: {e}")

		if user is None or guild is None or reason is None :
			logging.warning(
				f"Skipping pending ban {wait_id}: missing data "
				f"(user={user}, guild={guild}, reason={reason!r})")
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
			logging.error(
				f"Failed to build/queue pending-ban embed for {user_id} in {guild_id}: {e}",
				exc_info=True)
	logging.info(f"Pending bans: queued {len(found_bans)} for review.")
	if len(found_bans) < 1 :
		await send_message(channel, f"No pending bans, good job team!", error_mode='ignore')
		return
	await send_message(channel, f"Heres the pending bans <@&{os.getenv('STAFF_ROLE')}>!", error_mode='warn')
