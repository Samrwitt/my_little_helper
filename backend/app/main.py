from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging

setup_logging()
settings = get_settings()

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Agentic AI scholarship discovery, eligibility matching, and deadline tracking",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name}
