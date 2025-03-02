import os

import discord

from classes.cacher import LongTermCache
from classes.queue import queue
from classes.support.discord_tools import send_message
from database.current import Bans
from database.databaseController import BanDbTransactions
from view.buttons.banapproval import BanApproval


async def pending_bans(bot, revoked=False):
    bans = BanDbTransactions().get_all_pending()
    channel = bot.get_channel(bot.BANCHANNEL)
    ban: Bans

    if revoked:
        await send_message(channel, "fetching pending bans after revoking ban")
    for ban in bans:
        if ban.approved is True or ban.hidden is True:
            continue
        reason = ban.reason
        wait_id = ban.ban_id
        user_id =  ban.uid
        guild_id = ban.gid
        user = bot.get_user(user_id)
        guild = bot.get_guild(guild_id)

        # If the user is not found in the cache, fetch from the API
        if user is None:
            print(f"User with ID {user_id} not found in cache.")
            try:
                user = await bot.fetch_user(user_id)
            except discord.NotFound:
                print(f"User with ID {user_id} not found.")
            except discord.HTTPException as e:
                print(f"Failed to fetch user with ID {user_id}: {e}")

        # If the guild is not found in the cache, fetch from the API
        if guild is None:
            print(f"Guild with ID {guild_id} not found in cache.")
            try:
                guild = await bot.fetch_guild(guild_id)
            except discord.NotFound:
                print(f"Guild with ID {guild_id} not found.")
            except discord.HTTPException as e:
                print(f"Failed to fetch guild with ID {guild_id}: {e}")

        if user is None or guild is None or reason is None:
            print(f"Error: {user} {guild} {reason}")
            continue
        try:
            embed = discord.Embed(title=f"{user} ({user.id}) was banned in {guild}({guild.owner})",
                                  description=f"{reason}")
            embed.set_footer(text=f"/approve_ban {wait_id}")
            queue().add(channel.send(f"<@&{os.getenv('STAFF_ROLE')}>",embed=embed, view=BanApproval(bot, wait_id, True)), priority=2)
        except Exception as e:
            print(f"Error: {e}")