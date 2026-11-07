import os
import sys
import asyncio

# On Windows, asyncio subprocesses (used by every scanner tool) only work on
# the Proactor event loop. uvicorn may otherwise select a Selector loop, on
# which create_subprocess_exec raises NotImplementedError. Force Proactor here,
# before uvicorn creates its event loop.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.database import init_db
from app.api.v1.targets import router as targets_router
from app.api.v1.scans import router as scans_router
from app.api.v1.ai import router as ai_router
from app.api.websocket import socketio_app
import uvicorn

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the Beanie/MongoDB connection on startup
    await init_db()
    yield

app = FastAPI(title="Pentest Scanner Orchestrator", lifespan=lifespan)

# CORS: comma-separated list of allowed frontend origins, e.g.
#   ALLOWED_ORIGINS=https://your-app.vercel.app
# Defaults to "*" (any origin) for local development.
_origins = [o.strip().rstrip("/") for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(targets_router, prefix="/api/v1/targets", tags=["targets"])
app.include_router(scans_router, prefix="/api/v1/scans", tags=["scans"])
app.include_router(ai_router, prefix="/api/v1/ai", tags=["ai"])

# Mount Socket.IO ASGI app at /socket.io to handle WS communication
app.mount("/socket.io", socketio_app)

@app.get("/")
async def root():
    return {"status": "online", "message": "Pentest Scanner Orchestrator is running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
