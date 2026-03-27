"""
MassEdit Backend - FastAPI Application Entry Point

A prompt-driven mass video editor powered by Claude AI.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from dotenv import load_dotenv

from models.database import get_database
from services.render_queue import get_render_queue

# Import routers
from routers import projects, boxes, interpret, render

# ============================================================================
# Configuration
# ============================================================================

# Load environment variables
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
STORAGE_PATH = os.getenv("MASSEDIT_STORAGE_PATH", "./storage")
MAX_CONCURRENT_RENDERS = int(os.getenv("MASSEDIT_MAX_CONCURRENT_RENDERS", "3"))
MAX_OUTPUT_COUNT = int(os.getenv("MASSEDIT_MAX_OUTPUT_COUNT", "5000"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# Lifespan Handler
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown.
    """
    # Startup
    logger.info("MassEdit backend starting...")

    # Validate API key
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set — AI interpretation will be unavailable until configured")

    # Create storage directories first (DB goes here too)
    storage_path = Path(STORAGE_PATH)
    storage_path.mkdir(parents=True, exist_ok=True)

    # Initialize database
    db_path = storage_path / "massedit.db"
    db = get_database(database_url=f"sqlite+aiosqlite:///{db_path}")
    await db.init_db()
    (storage_path / "clips").mkdir(exist_ok=True)
    (storage_path / "thumbnails").mkdir(exist_ok=True)
    (storage_path / "outputs").mkdir(exist_ok=True)

    logger.info(f"Storage path: {storage_path}")
    logger.info(f"Max concurrent renders: {MAX_CONCURRENT_RENDERS}")
    logger.info(f"Max output count: {MAX_OUTPUT_COUNT}")

    # Initialize render queue
    queue = get_render_queue(max_concurrent=MAX_CONCURRENT_RENDERS)

    logger.info("MassEdit backend ready")

    yield

    # Shutdown
    logger.info("MassEdit backend shutting down...")

    await queue.stop_processing()
    await db.close()

    logger.info("MassEdit backend stopped")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="MassEdit Backend",
    description="Prompt-driven mass video editor powered by Claude AI",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(boxes.router, prefix="/api", tags=["boxes"])
app.include_router(interpret.router, prefix="/api", tags=["interpret"])
app.include_router(render.router, prefix="/api", tags=["render"])


# ============================================================================
# Static File Serving
# ============================================================================

storage_path = Path(STORAGE_PATH)

# Mount output directory
outputs_dir = storage_path / "outputs"
if outputs_dir.exists():
    app.mount(
        "/outputs",
        StaticFiles(directory=outputs_dir),
        name="outputs",
    )

# Mount thumbnails directory
thumbnails_dir = storage_path / "thumbnails"
if thumbnails_dir.exists():
    app.mount(
        "/thumbnails",
        StaticFiles(directory=thumbnails_dir),
        name="thumbnails",
    )


# ============================================================================
# WebSocket Endpoint
# ============================================================================

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
import json

class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        """Accept and track a WebSocket connection."""
        await websocket.accept()
        self.active_connections[job_id] = websocket
        logger.info(f"WebSocket connected: job {job_id}")

    def disconnect(self, job_id: str):
        """Remove a WebSocket connection."""
        if job_id in self.active_connections:
            del self.active_connections[job_id]
            logger.info(f"WebSocket disconnected: job {job_id}")

    async def broadcast_progress(self, job_id: str, progress: int):
        """Broadcast progress update to connected client."""
        if job_id in self.active_connections:
            try:
                await self.active_connections[job_id].send_json({
                    "type": "progress",
                    "job_id": job_id,
                    "progress": progress,
                })
            except Exception as e:
                logger.error(f"WebSocket send error: {e}")
                self.disconnect(job_id)

    async def broadcast_complete(self, job_id: str, success: bool, output_path: str = None):
        """Broadcast job completion to connected client."""
        if job_id in self.active_connections:
            try:
                await self.active_connections[job_id].send_json({
                    "type": "complete",
                    "job_id": job_id,
                    "success": success,
                    "output_path": output_path,
                })
            except Exception as e:
                logger.error(f"WebSocket send error: {e}")
                self.disconnect(job_id)


manager = ConnectionManager()


@app.websocket("/ws/render/{job_id}")
async def websocket_render_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time render progress.

    Path:
        /ws/render/{job_id}

    Receives:
        Progress updates and completion notifications

    Example client:
        const ws = new WebSocket('ws://localhost:8000/ws/render/job-123');
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'progress') {
                console.log(`Progress: ${data.progress}%`);
            } else if (data.type === 'complete') {
                console.log(`Complete: ${data.success}`);
            }
        };
    """
    await manager.connect(job_id, websocket)

    try:
        while True:
            # Keep connection alive, wait for messages
            data = await websocket.receive_text()
            logger.debug(f"WebSocket message from {job_id}: {data}")

    except WebSocketDisconnect:
        manager.disconnect(job_id)


# ============================================================================
# Health Check Endpoint
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "MassEdit Backend",
        "version": "0.1.0",
    }


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "MassEdit Backend",
        "description": "Prompt-driven mass video editor powered by Claude AI",
        "docs": "/docs",
        "health": "/health",
    }


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
