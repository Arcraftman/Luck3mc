"""Server-Sent Events stream for real-time frontend updates."""
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..events import bus

router = APIRouter(tags=["stream"])


@router.get("/api/stream")
async def stream():
    async def event_generator():
        q = await bus.connect()
        try:
            yield ": connected\n\n"
            while True:
                message = await q.get()
                yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
        finally:
            bus.disconnect(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
