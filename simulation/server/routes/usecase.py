"""Use case routes — standardisation and readiness impact analysis."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.routes.delegates import get_engine

router = APIRouter(prefix="/game", tags=["use-case"])


class UseCaseRequest(BaseModel):
    usecase_text: str


@router.post("/{session_id}/standardise")
async def standardise_usecase(session_id: str, req: UseCaseRequest):
    """Standardise a use case against the ITU-T Y.3172 ML pipeline.

    Maps the use case to 6 pipeline nodes (SRC, Collector, Preprocessor,
    ML Function, SINK, Sandbox), generates requirements, and identifies gaps.

    Examples:
    - "Animal husbandry automation using IoT sensors for preventive disease management"
    - "Smart traffic management using computer vision and edge AI"
    - "Crop yield prediction using satellite imagery and weather data"
    """
    engine = get_engine()
    session = engine.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return engine.standardise_usecase(session_id, req.usecase_text)


@router.post("/{session_id}/readiness")
async def usecase_readiness(session_id: str, req: UseCaseRequest):
    """Analyse a use case's impact on AI Readiness dimensions.

    Uses Y.3172 pipeline mapping to determine which readiness dimensions
    are affected, then routes through standard agents and causal graph
    for full impact analysis (similar to a what-if scenario).

    Examples:
    - "Deploy IoT sensors across 10,000 farms for livestock health monitoring"
    - "Build a national AI chatbot for government services in local languages"
    """
    engine = get_engine()
    session = engine.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return engine.usecase_readiness(session_id, req.usecase_text)
