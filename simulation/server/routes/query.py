"""Query routes — clarification questions about the framework."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.routes.delegates import get_engine

router = APIRouter(prefix="/game", tags=["queries"])


class ClarifyRequest(BaseModel):
    question: str


@router.post("/{session_id}/clarify")
async def clarify(session_id: str, req: ClarifyRequest):
    """Ask a clarification question about the AI Readiness framework.

    The question is routed to the relevant agent(s) based on content.
    Examples:
    - "How does R&D investment map to Dimension 3?"
    - "What metrics are used for Digital Infrastructure?"
    - "Explain the relationship between data marketplace and cross-domain analysis"
    """
    engine = get_engine()
    session = engine.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return engine.clarify(session_id, req.question)
