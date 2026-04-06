"""FastAPI entry point for the AI Readiness Simulation Game."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from server.config import settings
from server.database import create_db_and_tables
from server.routes import dashboard, decisions, delegates, query, whatif

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Manages WebSocket connections for real-time delegate notifications."""

    def __init__(self):
        self._connections: dict[str, WebSocket] = {}  # session_id -> ws

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self._connections[session_id] = websocket

    def disconnect(self, session_id: str):
        self._connections.pop(session_id, None)

    async def send_to(self, session_id: str, message: dict[str, Any]):
        ws = self._connections.get(session_id)
        if ws:
            await ws.send_json(message)

    async def broadcast(self, message: dict[str, Any], exclude: Optional[str] = None):
        for sid, ws in list(self._connections.items()):
            if sid != exclude:
                try:
                    await ws.send_json(message)
                except Exception:
                    self._connections.pop(sid, None)

    @property
    def active_count(self) -> int:
        return len(self._connections)


ws_manager = ConnectionManager()


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.chromadb_dir.mkdir(parents=True, exist_ok=True)
    settings.docs_dir.mkdir(parents=True, exist_ok=True)
    create_db_and_tables()
    print(f"AI Readiness Simulation Game server starting on {settings.host}:{settings.port}")
    print(f"Database: {settings.db_path}")
    print(f"ChromaDB: {settings.chromadb_dir}")
    print(f"API docs: http://localhost:{settings.port}/docs")
    yield
    print("Server shutting down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Readiness Simulation Game",
    description=(
        "Multi-delegate simulation game for ITU AI Readiness Framework assessment.\n\n"
        "**Delegates** register, submit country scenarios, ask clarifications, "
        "run what-if analyses, and announce policy decisions.\n\n"
        "**6 AI Agents** (Dataset, OpenSource, Sandbox, Research, Deployment, Standards) "
        "assess 13 dimensions using RAG over a Knowledge Base of 27+ international documents.\n\n"
        "**Causal Graph** propagates effects between interdependent dimensions."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow all origins for prototype
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include routers ---
app.include_router(delegates.router)
app.include_router(query.router)
app.include_router(whatif.router)
app.include_router(decisions.router)
app.include_router(dashboard.router)


# --- Root & health ---

@app.get("/", tags=["system"])
async def root():
    return {
        "name": "AI Readiness Simulation Game",
        "version": "0.1.0",
        "framework": "ITU AI Ready Framework 2.0 (January 2026)",
        "dimensions": 13,
        "factors": 6,
        "agents": 6,
        "status": "running",
        "docs": f"http://localhost:{settings.port}/docs",
    }


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "websocket_connections": ws_manager.active_count}


# --- WebSocket ---

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket for real-time notifications.

    Delegates connect here to receive live updates when:
    - Another delegate makes a decision
    - Scores are recalculated
    - New delegates join
    """
    await ws_manager.connect(session_id, websocket)
    try:
        # Notify others
        await ws_manager.broadcast(
            {"event": "delegate_connected", "session_id": session_id},
            exclude=session_id,
        )
        # Keep connection alive, relay any messages
        while True:
            data = await websocket.receive_text()
            # Echo back for now; can be extended for delegate-to-delegate messaging
            await ws_manager.send_to(session_id, {"event": "ack", "data": data})
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id)
        await ws_manager.broadcast(
            {"event": "delegate_disconnected", "session_id": session_id},
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
