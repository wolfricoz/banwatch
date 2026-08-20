# my_discord_bot/routes/example_routes.py
import logging
from typing import Optional

from discord.ext import commands
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.auth.auth import Auth
from classes.config.utils import ConfigUtils
from classes.configdata import ConfigData
from classes.queue import queue

router = APIRouter()

logger = logging.getLogger(__name__)


class BanRequest(BaseModel) :
	id: int
	token: str


# NOTE: these paths are lowercase because routing is case-sensitive. This was registered as
# "/Config/refresh" while the dashboard has always posted to "/config/refresh", so every config
# save made from the website 404'd here and the bot was never told anything had changed.
@router.post("/config/refresh", )
async def refresh_config_all(request: Request) :
	"""Drops the whole config cache. Prefer the per-guild route below."""
	if not await Auth(request).verify() :
		# the error is usually raised in the verify function, but this is just a final catch.
		raise HTTPException(status_code=403)
	logger.info("Website Request: Reload Config (all guilds)")
	ConfigData().reload()
	return {"status" : "success", "message" : "Config reloaded"}


@router.post("/config/refresh/{guildid}")
async def refresh_config(request: Request, guildid: Optional[int]) :
	if not await Auth(request).verify() :
		# the error is usually raised in the verify function, but this is just a final catch.
		raise HTTPException(status_code=403)

	logger.info("Website Request: Reload Config")
	if guildid is None :
		logging.info("[Config API] guildid not provided")
		return {"error" : "Guild ID is required"}
	ConfigData().load_guild(guildid)
	return {"message" : f"Config refresh queued for {guildid}"}


@router.post("/config/{guildid}/changes/log")
async def log_config_changes(request: Request, guildid: int, changes: dict, user_name: str = "dashboard_api") :
	if not await Auth(request).verify() :
		# the error is usually raised in the verify function, but this is just a final catch.
		raise HTTPException(status_code=403)

	bot: commands.Bot = request.app.state.bot
	guild = bot.get_guild(guildid)
	if not guild :
		return {"message" : "Guild not found"}
	# ageverifier awaits this directly because its bot shares the API's event loop. Ours runs on
	# its own loop in a separate thread, so the coroutine goes to the queue - which the bot drains
	# on its own loop - rather than being awaited here.
	queue().add(ConfigUtils.log_change(guild, changes, user_name), priority=1)
	return {"message" : f"Configuration changes for {guild.name} logged"}
