# my_discord_bot/routes/example_routes.py
import logging
import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.auth.auth import Auth
from classes.configdata import ConfigData

router = APIRouter()


class BanRequest(BaseModel) :
	id: int
	token: str



@router.post("/Config/refresh", )
async def bans_get(request: Request) :
	if not await Auth(request).verify() :
		# the error is usually raised in the verify function, but this is just a final catch.
		raise HTTPException(status_code=403)
	ConfigData().reload()
	return {"status": "success", "message": "Config reloaded"}