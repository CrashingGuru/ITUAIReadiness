"""Structured scoring — aggregation, maturity levels, and composite scores.

Takes AgentResponse outputs and produces a unified CountryScenario
with all 13 dimensions scored.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from server.models import (
    AgentResponse,
    CountryScenario,
    DimensionScore,
    InputMethod,
)

logger = logging.getLogger(__name__)

# Maturity level labels
MATURITY_LEVELS = {
    0: "Not Started",
    1: "Initial / Ad-hoc",
    2: "Developing",
    3: "Established",
    4: "Advanced",
    5: "Leading / Optimizing",
}


def maturity_label(score: float) -> str:
    """Convert a 0-5 score to a maturity level label."""
    rounded = round(score)
    return MATURITY_LEVELS.get(max(0, min(5, rounded)), "Unknown")


def aggregate_agent_responses(
    responses: list[AgentResponse],
    country_name: str,
    delegate_id: str,
    raw_input: str = "",
    input_method: InputMethod = InputMethod.NARRATIVE,
) -> CountryScenario:
    """Aggregate multiple agent responses into a single CountryScenario.

    For each dimension (1-13):
    - If scored by an agent, use the highest-confidence score
    - If not scored, mark as unassessed (score=-1, confidence=0)
    """
    # Collect all scores keyed by dimension_id
    best_scores: dict[int, DimensionScore] = {}

    for resp in responses:
        for score in resp.scores:
            dim_id = score.dimension_id
            if dim_id < 1 or dim_id > 13:
                continue
            if dim_id not in best_scores or score.confidence > best_scores[dim_id].confidence:
                best_scores[dim_id] = score

    # Build full 13-dimension list
    from server.knowledge.dimensions import get_dimension_names
    dim_names = get_dimension_names()

    dimensions: list[DimensionScore] = []
    for dim_id in range(1, 14):
        if dim_id in best_scores:
            dimensions.append(best_scores[dim_id])
        else:
            dimensions.append(DimensionScore(
                dimension_id=dim_id,
                dimension_name=dim_names.get(dim_id, f"Dimension {dim_id}"),
                score=0.0,
                evidence=[],
                confidence=0.0,
                gaps=["Not assessed by any agent"],
                recommendations=["Provide more information about this dimension"],
            ))

    scenario = CountryScenario(
        country_name=country_name,
        delegate_id=delegate_id,
        dimensions=dimensions,
        raw_input=raw_input,
        input_method=input_method,
        timestamp=datetime.utcnow(),
    )
    scenario.compute_overall()
    return scenario


def compute_composite_score(
    scenario: CountryScenario,
    weights: Optional[dict[int, float]] = None,
) -> float:
    """Compute weighted composite score across all dimensions.

    Parameters
    ----------
    scenario : CountryScenario
        The scenario to score.
    weights : dict[int, float], optional
        Dimension weights (indices). Keys are dimension IDs (1-13),
        values are weights (0-1). Unweighted dimensions default to 1.0.

    Returns
    -------
    float
        Weighted average score (0-5).
    """
    if not scenario.dimensions:
        return 0.0

    weights = weights or {}
    total_weight = 0.0
    weighted_sum = 0.0

    for dim in scenario.dimensions:
        w = weights.get(dim.dimension_id, 1.0)
        if w <= 0:
            continue  # filtered out by 0/1 index
        weighted_sum += dim.score * w
        total_weight += w

    if total_weight == 0:
        return 0.0

    return weighted_sum / total_weight


def compute_gap_analysis(scenario: CountryScenario) -> list[dict[str, Any]]:
    """Identify the biggest gaps and produce prioritized recommendations.

    Returns a list of gap entries sorted by severity (lowest score first).
    """
    gaps: list[dict[str, Any]] = []

    for dim in scenario.dimensions:
        if dim.score < 3.0:  # below "Established" level
            gaps.append({
                "dimension_id": dim.dimension_id,
                "dimension_name": dim.dimension_name,
                "score": dim.score,
                "maturity": maturity_label(dim.score),
                "gaps": dim.gaps,
                "recommendations": dim.recommendations,
                "priority": "HIGH" if dim.score < 1.5 else "MEDIUM",
            })

    return sorted(gaps, key=lambda g: g["score"])


def scenario_summary(scenario: CountryScenario) -> dict[str, Any]:
    """Produce a human-readable summary of a country scenario."""
    assessed = [d for d in scenario.dimensions if d.confidence > 0]
    unassessed = [d for d in scenario.dimensions if d.confidence == 0]

    return {
        "country": scenario.country_name,
        "overall_score": round(scenario.overall_score or 0, 2),
        "overall_maturity": maturity_label(scenario.overall_score or 0),
        "dimensions_assessed": len(assessed),
        "dimensions_unassessed": len(unassessed),
        "scores": {
            d.dimension_name: {
                "score": round(d.score, 2),
                "maturity": maturity_label(d.score),
                "confidence": round(d.confidence, 2),
            }
            for d in scenario.dimensions
        },
        "top_strengths": [
            {"dimension": d.dimension_name, "score": round(d.score, 2)}
            for d in sorted(assessed, key=lambda x: -x.score)[:3]
        ],
        "top_gaps": compute_gap_analysis(scenario)[:5],
        "timestamp": scenario.timestamp.isoformat(),
    }


def compare_scenarios(
    before: CountryScenario,
    after: CountryScenario,
) -> dict[str, Any]:
    """Compare two scenarios (e.g., before/after a what-if or decision).

    Returns dimension-by-dimension delta with direction indicators.
    """
    before_map = {d.dimension_id: d for d in before.dimensions}
    after_map = {d.dimension_id: d for d in after.dimensions}

    deltas: list[dict[str, Any]] = []
    for dim_id in range(1, 14):
        b = before_map.get(dim_id)
        a = after_map.get(dim_id)
        if b and a:
            delta = a.score - b.score
            deltas.append({
                "dimension_id": dim_id,
                "dimension_name": a.dimension_name,
                "before": round(b.score, 2),
                "after": round(a.score, 2),
                "delta": round(delta, 2),
                "direction": "+" if delta > 0 else ("-" if delta < 0 else "="),
            })

    overall_before = before.overall_score or 0
    overall_after = after.overall_score or 0

    return {
        "country": after.country_name,
        "overall_before": round(overall_before, 2),
        "overall_after": round(overall_after, 2),
        "overall_delta": round(overall_after - overall_before, 2),
        "dimensions": deltas,
        "improved": [d for d in deltas if d["delta"] > 0],
        "declined": [d for d in deltas if d["delta"] < 0],
        "unchanged": [d for d in deltas if d["delta"] == 0],
    }
