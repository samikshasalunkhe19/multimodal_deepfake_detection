"""FastAPI application.

Run from the project folder:

    uvicorn backend.main:app --reload --port 8000

Interactive API docs: http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import ensure_directories, settings
from backend.routes import analyze, health, history
from database.session import init_db
from utils.file_validation import ValidationError
from utils.logging_config import setup_logging
from utils.temp_files import cleanup_stale_files

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_directories()
    setup_logging()
    init_db()
    removed = cleanup_stale_files()
    if removed:
        logger.info("Removed %d stale temporary file(s)", removed)
    logger.info("Backend ready")
    yield


app = FastAPI(
    title="Image & Video Deepfake Detection API",
    version="0.1.0",
    description="Risk estimates for images and videos. Results are estimates, not proof.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],   # Streamlit default
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    # The message is written to be safe to show to the user.
    return JSONResponse(status_code=400, content={"detail": str(exc)})


app.include_router(health.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(history.router, prefix="/api")
