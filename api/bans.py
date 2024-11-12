# my_discord_bot/routes/example_routes.py
import json
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database.databaseController import BanDbTransactions

router = APIRouter()


class BanRequest(BaseModel) :
	id: int
	token: str


@router.get("/example")
async def example_route() :
	return {"message" : "Hello from the example route!"}


@router.post("/bans/get/", )
async def bans_get(ban_request: BanRequest) :
	if ban_request.token != os.getenv("RPSECSECRET") :
		return HTTPException(404)
	bans = BanDbTransactions().get_all_user(ban_request.id)
	if bans is None :
		return HTTPException(404)
	return json.dumps({ban.ban_id : ban.message for ban in bans if ban.message is not None})
