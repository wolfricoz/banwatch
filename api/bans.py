# my_discord_bot/routes/example_routes.py
import json
import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import logging

from database.databaseController import BanDbTransactions

router = APIRouter()


class BanRequest(BaseModel) :
	id: int
	token: str


@router.get("/example")
async def example_route() :
	return {"message" : "Hello from the example route!"}


@router.post("/bans/get/", )
async def bans_get(ban_request: BanRequest, request: Request) :
	if ban_request.token != os.getenv("RPSECSECRET") :
		logging.warning(f"{request.client.host} failed to connect with {ban_request}, failed at token")
		return HTTPException(404)
	bans = BanDbTransactions().get_all_user(ban_request.id)
	bans = {ban.ban_id : ban.message for ban in bans if ban.message is not None}
	if bans is None or len(bans) < 1:
		logging.warning(f"{request.client.host} failed to connect with {ban_request}, No bans found")
		return HTTPException(404, detail="No bans found for this user id")
	logging.info(f"{request.client.host} connected with {ban_request} and returned {bans}")
	return json.dumps(bans)
