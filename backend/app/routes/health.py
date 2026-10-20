from fastapi import APIRouter, Request

from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    deps = request.app.state.deps
    return HealthResponse(status="ok", mode=deps.settings.mode, llm_provider=deps.llm.name,
                          mongo=deps.mongo_kind, redis=deps.redis_kind)
