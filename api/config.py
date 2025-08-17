# my_discord_bot/routes/example_routes.py
import logging
import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from classes.configdata import ConfigData

router = APIRouter()


class BanRequest(BaseModel) :
	id: int
	token: str



@router.post("/config/refresh", )
async def bans_get(request: Request) :
	if request.headers.get('token') != os.getenv("RPSECSECRET") :
		logging.warning(f"Invalid token {request.headers.get('token')} from {request.client.host}")
		return HTTPException(404)
	ConfigData().reload()
	return {"status": "success", "message": "Config reloaded"}