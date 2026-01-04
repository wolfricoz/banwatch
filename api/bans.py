# my_discord_bot/routes/example_routes.py
import json
import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import logging

from database.transactions.BanTransactions import BanDbTransactions

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


@router.get("/bans/count/{user_id}", )
async def bans_get(user_id: int, request: Request) :
	# Currently only used by ageverifier, however if this goes public then it needs rate limiting.

	if user_id is None or 16 < user_id < 19:
		return HTTPException(404)
	ban_count = BanDbTransactions().count_all_user(user_id)
	return json.dumps({"bans" : ban_count})