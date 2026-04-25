import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.auth.auth import Auth
from database.transactions.ServerTransactions import ServerTransactions

router = APIRouter(prefix="/premium")

logger = logging.getLogger(__name__)

class ServerUpdate(BaseModel) :
	serverId: int
	premium: datetime


@router.put("/update")
async def update_premium(request: Request, data: list[ServerUpdate]) :
	if not await Auth(request).verify() :
		# the error is usually raised in the verify function, but this is just a final catch.
		raise HTTPException(status_code=403)
	logging.info(f"Received {len(data)} premium updates.")
	for server in data :
		await asyncio.to_thread(ServerTransactions().update,
		                        server.serverId,
		                        premium=server.premium)

	return {"message" : "ok"}
