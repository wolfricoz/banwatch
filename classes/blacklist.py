import logging

import discord

from classes.configer import Configer
from classes.queue import queue
from classes.support.discord_tools import send_message


async def blacklist_check(guild: discord.Guild, log: discord.TextChannel) -> bool:

    if await Configer.is_blacklisted(guild.id):
        logging.info(f"Leaving {guild.name} because it is blacklisted")
        queue().add(send_message(log, f"Leaving {guild}({guild.id}) because it is blacklisted"))
        await guild.leave()
        # await log.send(f"[DEV MODE] Leaving disabled for testing")
        return True
    if await Configer.is_user_blacklisted(guild.owner.id):
        logging.info(f"Leaving {guild.name} because the {guild.owner.name}({guild.owner.id}) is blacklisted")
        queue().add(send_message(log, f"Leaving {guild}({guild.id}) because the {guild.owner.name}({guild.owner.id}) is blacklisted"))
        await Configer.add_to_blacklist(guild.id)
        # await log.send(f"[DEV MODE] Leaving disabled for testing")
        await guild.leave()
        return True
    return False
