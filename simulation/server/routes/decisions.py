"""Decision routes — policy/strategy announcements by delegates."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.routes.delegates import get_engine

router = APIRouter(prefix="/game", tags=["decisions"])


class DecisionRequest(BaseModel):
    decision_text: str


@router.post("/{session_id}/decide")
async def announce_decision(session_id: str, req: DecisionRequest):
    """Announce a policy, strategy, or roadmap decision.

    The decision is:
    1. Assessed by agents for impact on dimensions
    2. Recorded in the Knowledge Base (kb_decisions collection)
    3. Dimension scores recalculated with causal propagation
    4. Logged to the audit trail

    Examples:
    - "We will launch a national open data portal by 2027"
    - "Ethiopia will invest $50M in AI research centers over 5 years"
    - "We will mandate AI ethics training for all government employees"
    """
    engine = get_engine()
    session = engine.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return engine.decide(session_id, req.decision_text)


@router.get("/{session_id}/decisions")
async def list_decisions(session_id: str):
    """List all decisions made by a delegate."""
    engine = get_engine()
    decisions = engine.sessions.get_decisions(session_id=session_id)
    return [
        {
            "id": d.id,
            "text": d.decision_text,
            "affected_dimensions": d.affected_dimensions,
            "timestamp": d.timestamp.isoformat(),
            "applied": d.applied,
        }
        for d in decisions
    ]
