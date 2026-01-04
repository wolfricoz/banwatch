import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from database.transactions.BanTransactions import BanDbTransactions

load_dotenv('main.env')
app = FastAPI()

class BanRequest(BaseModel):
	id: int
	token: str



@app.get("/test")
async def root():
	return {'message': "Welcome!"}

@app.post("/bans/get/", )
async def bans_get(ban_request: BanRequest):
	if ban_request.token != os.getenv("RPSECSECRET"):
		return HTTPException(404)
	bans = BanDbTransactions().get_all_user(ban_request.id)
	if bans is None:
		return HTTPException(404)
	return json.dumps({ban.ban_id: ban.message for ban in bans if ban.message is not None})