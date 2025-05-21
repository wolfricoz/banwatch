# my_discord_bot/routes/example_routes.py

from fastapi import APIRouter
from classes.queue import queue

router = APIRouter()


@router.post("/ping")
async def ping() :
	q = queue()
	return {
		"status"                : "alive",
		"high_priority_queue"   : len(q.high_priority_queue),
		"normal_priority_queue" : len(q.normal_priority_queue),
		"low_priority_queue"    : len(q.low_priority_queue),
	}
