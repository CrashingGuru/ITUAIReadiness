"""What-if routes — policy/strategy scenario analysis."""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.routes.delegates import get_engine

router = APIRouter(prefix="/game", tags=["what-if"])


class WhatIfRequest(BaseModel):
    question: str
    hypothetical_changes: Optional[dict[str, Any]] = None


@router.post("/{session_id}/whatif")
async def whatif_analysis(session_id: str, req: WhatIfRequest):
    """Run a what-if analysis on a policy or strategy change.

    Creates a transient Knowledge Cache, agents reason against it
    with KB as base, causal graph propagates effects, then cache
    is discarded.

    Examples:
    - "What if we invest $100M in 5G infrastructure?"
    - "What if we mandate open data for all government agencies?"
    - "What if we establish 3 new AI research centers?"
    """
    engine = get_engine()
    session = engine.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return engine.whatif(session_id, req.question, req.hypothetical_changes)


@router.post("/{session_id}/impact-preview")
async def impact_preview(session_id: str, dimension_id: int, delta: float):
    """Preview how a score change in one dimension cascades to others.

    Quick lookup against the causal graph without running agents.
    """
    engine = get_engine()
    if dimension_id < 1 or dimension_id > 13:
        raise HTTPException(status_code=400, detail="dimension_id must be 1-13")
    return engine.causal.impact_preview(dimension_id, delta)
