import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.routes import briefing, history, meeting, research
from app.config import settings
from app.database.connection import SessionLocal, engine, init_db
from app.models import Meeting
from app.utils.logging_config import setup_logging

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    # A server restart kills in-flight background jobs; don't leave meetings stuck on "researching"
    with SessionLocal() as db:
        stuck = db.query(Meeting).filter(Meeting.status == "researching").update(
            {"status": "failed", "progress_stage": "failed",
             "error_message": "Research was interrupted by a server restart. Please run it again."}
        )
        db.commit()
        if stuck:
            logger.warning("Marked %d interrupted meeting(s) as failed", stuck)
    logger.info("MeetWise AI started (env=%s)", settings.environment)
    yield


# Create FastAPI application
app = FastAPI(
    title="MeetWise AI",
    description="AI-powered Pre-Meeting Briefing Agent",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow frontend to communicate with backend (origins come from CORS_ORIGINS in .env)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)
# Route order matters: static paths (/preview, /stats) are declared before /{id} routes
app.include_router(meeting.router)
app.include_router(research.router)
app.include_router(briefing.router)
app.include_router(history.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Log the real error server-side; never leak internals to the client
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Root endpoint
@app.get("/")
def home():
    return {
        "message": "Welcome to MeetWise AI Backend!",
        "status": "Running successfully"
    }


# Health check endpoint (extra fields are additive, existing keys unchanged)
@app.get("/health")
def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        logger.exception("Database health check failed")
        db_status = "unavailable"

    return {
        "status": "healthy" if db_status == "ok" else "degraded",
        "application": "MeetWise AI",
        "database": db_status,
        "mock_mode": settings.mock_mode,
        # booleans only - the keys themselves are never exposed
        "tavily_configured": bool(settings.tavily_api_key),
        "anthropic_configured": bool(settings.anthropic_api_key),
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model_name,
        "llm_configured": settings.llm_configured,
    }
