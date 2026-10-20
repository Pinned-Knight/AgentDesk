import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.agent.graph import build_graph
from app.cache import Cache, connect_redis
from app.config import Settings, get_settings
from app.db import close_mongo, connect_mongo, ensure_indexes, seed
from app.deps import Deps
from app.llm import build_llm
from app.routes import analytics, chat, conversations, health

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    db, mongo_kind = await connect_mongo(settings)
    await ensure_indexes(db)
    if settings.seed_demo_data:
        await seed(db)
    redis, redis_kind = await connect_redis(settings)
    cache = Cache(redis, redis_kind, settings)
    llm = build_llm(settings)
    app.state.deps = Deps(db=db, cache=cache, llm=llm, graph=build_graph(db, llm), settings=settings,
                          mongo_kind=mongo_kind, redis_kind=redis_kind)
    app.state.tasks = set()
    try:
        yield
    finally:
        if hasattr(llm, "aclose"):
            await llm.aclose()
        await cache.close()
        await close_mongo(db)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="AgentDesk API", version=__version__, lifespan=lifespan,
                  description="AI customer-support agent: LangGraph workflow over MongoDB tools, Redis memory/cache.")
    app.state.settings = settings
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])
    for module in (health, chat, conversations, analytics):
        app.include_router(module.router, prefix="/api")
    return app


app = create_app()
