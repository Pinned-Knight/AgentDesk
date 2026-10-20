import asyncio
import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.agent.service import run_turn
from app.schemas import ChatRequest, ChatResponse

logger = logging.getLogger("agentdesk.chat")
router = APIRouter(tags=["chat"])


async def _rate_limited(request: Request) -> JSONResponse | None:
    client_id = request.client.host if request.client else "anonymous"
    allowed, retry_after = await request.app.state.deps.cache.check_rate_limit(client_id)
    if allowed:
        return None
    return JSONResponse({"detail": "Rate limit exceeded", "retry_after": retry_after}, status_code=429,
                        headers={"Retry-After": str(retry_after)})


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    if (blocked := await _rate_limited(request)) is not None:
        return blocked
    return await run_turn(request.app.state.deps, req)


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, request: Request):
    """Server-sent events: trace / tool / token events as the agent works, then a final `done`."""
    if (blocked := await _rate_limited(request)) is not None:
        return blocked
    deps = request.app.state.deps
    queue: asyncio.Queue = asyncio.Queue()

    async def emit(event: str, data: dict) -> None:
        await queue.put((event, data))

    async def worker() -> None:
        try:
            response = await run_turn(deps, req, emit)
            await queue.put(("done", response.model_dump()))
        except Exception:
            logger.exception("chat turn failed")
            await queue.put(("error", {"detail": "Something went wrong while generating a reply."}))
        finally:
            await queue.put(None)

    # Keep a strong reference so the turn still finishes (and persists) if the client disconnects.
    task = asyncio.create_task(worker())
    request.app.state.tasks.add(task)
    task.add_done_callback(request.app.state.tasks.discard)

    async def events():
        while (item := await queue.get()) is not None:
            event, data = item
            yield f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
