"""In-memory event bus for Server-Sent Events (SSE) fan-out.

Holds asyncio queues for each connected browser; ingest broadcasts new
policies/reports so the Vue frontend updates in real time.
"""
import asyncio
from typing import Any, List


class EventBus:
    def __init__(self) -> None:
        self._queues: List[asyncio.Queue] = []

    async def connect(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._queues.append(q)
        return q

    def disconnect(self, q: asyncio.Queue) -> None:
        if q in self._queues:
            self._queues.remove(q)

    async def broadcast(self, message: Any) -> None:
        for q in list(self._queues):
            await q.put(message)


bus = EventBus()
