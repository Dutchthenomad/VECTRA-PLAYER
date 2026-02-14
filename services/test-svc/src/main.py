"""Service entry point with FastAPI app."""

import asyncio
import logging
import os
import time

import uvicorn
from fastapi import FastAPI

from .feed import FeedManager
from .processor import Processor

logger = logging.getLogger(__name__)

app = FastAPI(title=os.getenv("SERVICE_NAME", "service"))

start_time = time.time()
processor = Processor()
feed_manager = FeedManager(processor=processor)
_background_tasks: set[asyncio.Task] = set()


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "uptime": time.time() - start_time,
    }


@app.get("/stats")
async def stats():
    return processor.get_stats()


@app.on_event("startup")
async def startup():
    task = asyncio.create_task(feed_manager.connect())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


@app.on_event("shutdown")
async def shutdown():
    await feed_manager.disconnect()


if __name__ == "__main__":
    port = int(os.getenv("SERVICE_PORT", "8000"))
    uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=False)
