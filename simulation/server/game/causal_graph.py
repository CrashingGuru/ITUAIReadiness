"""Causal graph — models interdependencies between the 13 AI Readiness dimensions.

When a what-if or decision changes one dimension's score, the graph
propagates weighted effects to downstream dimensions.

Example:
    D13 (Infra) +0.5  →  D5 (AI Integration) +0.25  →  D6 (Human Interface) +0.12
"""

from __future__ import annotations

import logging
from typing import Any

import networkx as nx

from server.models import DimensionScore

logger = logging.getLogger(__name__)

# Edge definitions: (source_dim, target_dim, weight)
# Weight represents how much a 1-point change in source propagates to target.
# Derived from the ITU framework's factor-dimension mappings and logical dependencies.
_CAUSAL_EDGES: list[tuple[int, int, float]] = [
    # Digital Infrastructure enables AI Integration
    (13, 5, 0.5),   # D13 (Infra) → D5 (AI Integration)
    (13, 6, 0.3),   # D13 (Infra) → D6 (Human Interface)
    (13, 11, 0.3),  # D13 (Infra) → D11 (AI for Inclusion)

    # Data Marketplace feeds Cross-domain and Contextualization
    (1, 2, 0.4),    # D1 (Data Marketplace) → D2 (Generated Content)
    (1, 3, 0.5),    # D1 (Data Marketplace) → D3 (Cross-domain)
    (1, 4, 0.3),    # D1 (Data Marketplace) → D4 (Contextualization)

    # Cross-domain enables Contextualization
    (3, 4, 0.4),    # D3 (Cross-domain) → D4 (Contextualization)

    # Strategy Alignment drives Integration and Priorities
    (7, 5, 0.4),    # D7 (Strategy) → D5 (AI Integration)
    (7, 12, 0.5),   # D7 (Strategy) → D12 (Granular Priorities)
    (7, 8, 0.3),    # D7 (Strategy) → D8 (Collaboration)

    # AI & Policy shapes Strategy and Collaboration
    (10, 7, 0.5),   # D10 (AI & Policy) → D7 (Strategy)
    (10, 8, 0.3),   # D10 (AI & Policy) → D8 (Collaboration)

    # Human Impact drives Collaboration and Integration
    (9, 8, 0.4),    # D9 (Human Impact) → D8 (Collaboration)
    (9, 5, 0.3),    # D9 (Human Impact) → D5 (AI Integration)

    # AI Integration influences Human Interface and Quality
    (5, 6, 0.4),    # D5 (AI Integration) → D6 (Human Interface)
    (5, 12, 0.3),   # D5 (AI Integration) → D12 (Granular Priorities)

    # Generated Content links to Inclusion
    (2, 11, 0.3),   # D2 (Generated Content) → D11 (AI for Inclusion)
    (2, 6, 0.3),    # D2 (Generated Content) → D6 (Human Interface)

    # Collaboration feeds back into Integration
    (8, 5, 0.2),    # D8 (Collaboration) → D5 (AI Integration)

    # AI for Inclusion links to Human Interface
    (11, 6, 0.3),   # D11 (Inclusion) → D6 (Human Interface)

    # Contextualization feeds Granular Priorities
    (4, 12, 0.4),   # D4 (Contextualization) → D12 (Granular Priorities)
]


class CausalGraph:
    """Directed weighted graph of dimension interdependencies."""

    def __init__(self):
        self.graph = nx.DiGraph()
        # Add all 13 dimensions as nodes
        for dim_id in range(1, 14):
            self.graph.add_node(dim_id)
        # Add causal edges
        for src, tgt, weight in _CAUSAL_EDGES:
            self.graph.add_edge(src, tgt, weight=weight)

    # ------------------------------------------------------------------
    # Propagation
    # ------------------------------------------------------------------

    def propagate(
        self,
        changes: dict[int, float],
        max_depth: int = 3,
        decay: float = 0.5,
    ) -> dict[int, float]:
        """Propagate score changes through the causal graph.

        Parameters
        ----------
        changes : dict[int, float]
            Initial changes: {dimension_id: score_delta}.
        max_depth : int
            Maximum propagation hops (prevents infinite loops).
        decay : float
            Additional decay factor per hop (multiplied with edge weight).

        Returns
        -------
        dict[int, float]
            Total accumulated changes for all affected dimensions,
            including the initial changes.
        """
        accumulated: dict[int, float] = dict(changes)
        frontier = dict(changes)

        for depth in range(max_depth):
            next_frontier: dict[int, float] = {}

            for dim_id, delta in frontier.items():
                # Propagate to all successors
                for successor in self.graph.successors(dim_id):
                    edge_weight = self.graph[dim_id][successor]["weight"]
                    propagated = delta * edge_weight * (decay ** depth)

                    # Only propagate if effect is meaningful (> 0.01)
                    if abs(propagated) < 0.01:
                        continue

                    if successor in next_frontier:
                        next_frontier[successor] += propagated
                    else:
                        next_frontier[successor] = propagated

            if not next_frontier:
                break

            # Accumulate
            for dim_id, delta in next_frontier.items():
                accumulated[dim_id] = accumulated.get(dim_id, 0.0) + delta

            frontier = next_frontier

        return accumulated

    def apply_propagation(
        self,
        scores: list[DimensionScore],
        changes: dict[int, float],
        max_depth: int = 3,
    ) -> list[DimensionScore]:
        """Apply propagated changes to a list of dimension scores.

        Returns a new list with updated scores (clamped to 0-5).
        """
        propagated = self.propagate(changes, max_depth=max_depth)

        score_map = {s.dimension_id: s for s in scores}
        updated: list[DimensionScore] = []

        for dim_id in range(1, 14):
            original = score_map.get(dim_id)
            if not original:
                continue

            delta = propagated.get(dim_id, 0.0)
            new_score = max(0.0, min(5.0, original.score + delta))

            updated.append(DimensionScore(
                dimension_id=original.dimension_id,
                dimension_name=original.dimension_name,
                score=round(new_score, 2),
                evidence=original.evidence + (
                    [f"Causal effect: {delta:+.2f} from propagation"]
                    if abs(delta) > 0.01 and dim_id not in changes
                    else []
                ),
                metrics=original.metrics,
                confidence=original.confidence,
                gaps=original.gaps,
                recommendations=original.recommendations,
            ))

        return updated

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def get_downstream(self, dim_id: int) -> list[tuple[int, float]]:
        """Get all direct downstream dimensions and their edge weights."""
        return [
            (succ, self.graph[dim_id][succ]["weight"])
            for succ in self.graph.successors(dim_id)
        ]

    def get_upstream(self, dim_id: int) -> list[tuple[int, float]]:
        """Get all direct upstream dimensions and their edge weights."""
        return [
            (pred, self.graph[pred][dim_id]["weight"])
            for pred in self.graph.predecessors(dim_id)
        ]

    def most_influential(self, top_n: int = 5) -> list[tuple[int, float]]:
        """Get the most influential dimensions by total outgoing weight."""
        influence: list[tuple[int, float]] = []
        for dim_id in range(1, 14):
            total_weight = sum(
                self.graph[dim_id][succ]["weight"]
                for succ in self.graph.successors(dim_id)
            )
            influence.append((dim_id, total_weight))
        return sorted(influence, key=lambda x: -x[1])[:top_n]

    def impact_preview(
        self,
        dim_id: int,
        delta: float,
    ) -> dict[str, Any]:
        """Preview the impact of changing one dimension by delta."""
        propagated = self.propagate({dim_id: delta})
        effects = {
            d: round(v, 3)
            for d, v in sorted(propagated.items())
            if d != dim_id and abs(v) >= 0.01
        }
        return {
            "source_dimension": dim_id,
            "direct_change": delta,
            "cascading_effects": effects,
            "total_dimensions_affected": len(effects),
        }

    def to_dict(self) -> dict[str, Any]:
        """Export the graph as a serializable dict."""
        return {
            "nodes": list(range(1, 14)),
            "edges": [
                {"from": u, "to": v, "weight": d["weight"]}
                for u, v, d in self.graph.edges(data=True)
            ],
        }
