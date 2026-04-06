"""Delegate routes — registration, scenario input, status."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from server.game.engine import GameEngine
from server.models import InputMethod, RegisterDelegateRequest, ScenarioInputRequest

router = APIRouter(prefix="/delegates", tags=["delegates"])

# Shared engine instance (initialized on first use)
_engine: Optional[GameEngine] = None


def get_engine() -> GameEngine:
    global _engine
    if _engine is None:
        _engine = GameEngine()
    return _engine


@router.post("/register")
async def register_delegate(req: RegisterDelegateRequest):
    """Register a new country delegate and create a session."""
    engine = get_engine()
    return engine.register_delegate(req.country_name, req.delegate_name)


@router.get("/")
async def list_delegates():
    """List all active delegates."""
    return get_engine().list_delegates()


@router.get("/{session_id}")
async def get_delegate(session_id: str):
    """Get a specific delegate's info and scenario summary."""
    return get_engine().get_dashboard(session_id)


@router.post("/{session_id}/scenario")
async def submit_scenario(session_id: str, req: ScenarioInputRequest):
    """Submit or update a country scenario for assessment.

    The input_text is analyzed by all 6 agents to produce dimension scores.
    """
    engine = get_engine()
    session = engine.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    if not req.input_text and not req.dimension_scores:
        raise HTTPException(status_code=400, detail="Provide input_text or dimension_scores")

    input_text = req.input_text or ""

    # If manual scores provided, format them as text for the agents
    if req.dimension_scores:
        score_lines = [f"Dimension {k}: {v}/5.0" for k, v in req.dimension_scores.items()]
        input_text = input_text + "\n\nManual dimension scores:\n" + "\n".join(score_lines)

    return engine.assess_country(session_id, input_text, req.input_method)


@router.post("/{session_id}/deactivate")
async def deactivate_delegate(session_id: str):
    """Deactivate a delegate session (delegate leaves the game)."""
    engine = get_engine()
    engine.sessions.deactivate_session(session_id)
    return {"status": "deactivated", "session_id": session_id}
