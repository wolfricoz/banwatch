import logging
import os

import discord
from discord_py_utilities.exceptions import NoPermissionException
from discord_py_utilities.messages import send_message

from classes.configdata import ConfigData
from database.transactions.ServerTransactions import ServerDbTransactions


async def inform_user(guild: discord.Guild, user: discord.User):
	appeal_status = ConfigData().get_key_or_none(guild.id, "allow_appeals")
	supguild = int(os.getenv('GUILD'))
	if not supguild:
		supguild = 1022307023527890974
	invite = ServerDbTransactions().get(supguild).invite
	reminder = f"You have recently been banned in \"{guild.name}\" and this has been recorded in Banwatch." + ("You can appeal your ban with `/appeal create`, if the ban is inaccurate you can report it **after** creating an appeal with `/appeal report`" if appeal_status else "This server doesn't allow appeals, if the ban is inaccurate you can report it **after** creating an appeal with `/appeal report`") + f"\n-# Reporting accurate bans is considered abuse of the Banwatch bot and can result in blacklisting. For further assistance, [join our support server](<{invite}>)"
	try:
		await send_message(user, reminder)
	except discord.errors.Forbidden or NoPermissionException:
		logging.error(f"Failed to send reminder to {user.name}")
	except Exception as e:
		logging.warning(f"Failed to send reminder to {user.name} because {e}")