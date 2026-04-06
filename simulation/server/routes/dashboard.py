"""Dashboard routes — scores, stats, causal graph, audit log."""

from typing import Optional

from fastapi import APIRouter, HTTPException

from server.routes.delegates import get_engine

router = APIRouter(prefix="/game", tags=["dashboard"])


@router.get("/{session_id}/dashboard")
async def get_dashboard(session_id: str):
    """Get the full dashboard for a delegate.

    Includes: current dimension scores, gap analysis, maturity levels,
    decision history, and overall readiness score.
    """
    engine = get_engine()
    session = engine.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return engine.get_dashboard(session_id)


@router.get("/{session_id}/scores")
async def get_scores(session_id: str, dimension_id: Optional[int] = None):
    """Get score history for a delegate, optionally filtered by dimension."""
    engine = get_engine()
    records = engine.sessions.get_score_history(session_id, dimension_id)
    return [
        {
            "dimension_id": r.dimension_id,
            "score": r.score,
            "confidence": r.confidence,
            "timestamp": r.timestamp.isoformat(),
        }
        for r in records
    ]


@router.get("/stats/overview")
async def get_stats():
    """Get overall game statistics: sessions, KB size, causal graph info."""
    return get_engine().get_stats()


@router.get("/graph/causal")
async def get_causal_graph():
    """Get the causal graph structure (nodes + weighted edges) for visualization."""
    return get_engine().get_causal_graph()


@router.get("/agents/list")
async def list_agents():
    """List all available agents and their dimension coverage."""
    return get_engine().router.list_agents()


@router.get("/kb/stats")
async def get_kb_stats():
    """Get Knowledge Base statistics (document counts per collection)."""
    return get_engine().kb.stats()


@router.get("/audit/log")
async def get_audit_log(limit: int = 50):
    """Get recent audit log entries."""
    engine = get_engine()
    entries = engine.sessions.get_audit_log(limit=limit)
    return [
        {
            "id": e.id,
            "timestamp": e.timestamp.isoformat(),
            "action": e.action,
            "user_id": e.user_id,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "new_value": e.new_value,
            "reason": e.reason,
        }
        for e in entries
    ]
