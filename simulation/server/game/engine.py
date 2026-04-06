"""Game engine — orchestrates the full simulation flow.

Ties together: sessions, agents, KB, cache, causal graph, and scoring.
Provides high-level methods for the three delegate interactions:
  1. Assessment (initial scenario input)
  2. What-If analysis
  3. Decision announcement
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from server.agents.router import AgentRouter
from server.game.causal_graph import CausalGraph
from server.game.scoring import (
    aggregate_agent_responses,
    compare_scenarios,
    compute_composite_score,
    compute_gap_analysis,
    scenario_summary,
)
from server.game.session import SessionManager
from server.knowledge.cache import KnowledgeCache
from server.knowledge.ingest import embed_texts
from server.knowledge.kb import KnowledgeBase
from server.models import (
    AgentResponse,
    ClarifyResponse,
    CountryScenario,
    DelegateDecision,
    DimensionScore,
    InputMethod,
    WhatIfQuery,
    WhatIfResult,
)

logger = logging.getLogger(__name__)


class GameEngine:
    """Central game engine orchestrating all simulation flows."""

    def __init__(self):
        self.kb = KnowledgeBase()
        self.cache = KnowledgeCache()
        self.sessions = SessionManager()
        self.causal = CausalGraph()
        self.router = AgentRouter(kb=self.kb, cache=self.cache)

    # ------------------------------------------------------------------
    # 1. Session management
    # ------------------------------------------------------------------

    def register_delegate(
        self,
        country_name: str,
        delegate_name: str,
    ) -> dict[str, Any]:
        """Register a new delegate and return session info."""
        session = self.sessions.create_session(country_name, delegate_name)
        return {
            "session_id": session.id,
            "country_name": session.country_name,
            "delegate_name": session.delegate_name,
            "created_at": session.created_at.isoformat(),
        }

    def list_delegates(self) -> list[dict[str, Any]]:
        """List all active delegates."""
        sessions = self.sessions.get_active_sessions()
        return [
            {
                "session_id": s.id,
                "country_name": s.country_name,
                "delegate_name": s.delegate_name,
                "has_scenario": s.scenario_json is not None,
            }
            for s in sessions
        ]

    # ------------------------------------------------------------------
    # 2. Assessment (initial scenario)
    # ------------------------------------------------------------------

    def assess_country(
        self,
        session_id: str,
        input_text: str,
        input_method: InputMethod = InputMethod.NARRATIVE,
    ) -> dict[str, Any]:
        """Run a full country assessment using all agents.

        Agents analyze the input text, score all 13 dimensions,
        and produce a CountryScenario.
        """
        session = self.sessions.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        logger.info("Assessing country %s for session %s", session.country_name, session_id)

        # Route to all agents for full assessment
        response = self.router.assess(input_text, session.country_name)

        # Aggregate into a CountryScenario
        scenario = aggregate_agent_responses(
            responses=[response],
            country_name=session.country_name,
            delegate_id=session_id,
            raw_input=input_text,
            input_method=input_method,
        )

        # Save to session
        self.sessions.save_scenario(session_id, scenario)

        return scenario_summary(scenario)

    # ------------------------------------------------------------------
    # 3. Clarification
    # ------------------------------------------------------------------

    def clarify(
        self,
        session_id: str,
        question: str,
    ) -> dict[str, Any]:
        """Answer a clarification question about the framework.

        Does NOT pass country context — clarifications are about the
        framework itself, not about a specific country's status.
        """
        response = self.router.clarify(question, country=None)

        return {
            "question": question,
            "answer": response.narrative,
            "related_dimensions": response.dimensions_assessed,
            "sources": response.sources_used,
            "agent": response.agent_name,
        }

    # ------------------------------------------------------------------
    # 4. What-If analysis
    # ------------------------------------------------------------------

    def whatif(
        self,
        session_id: str,
        question: str,
        hypothetical_changes: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Run a what-if analysis.

        Flow:
        1. Create cache session
        2. Snapshot relevant KB entries into cache
        3. Route to agents (who reason against cache with KB as base)
        4. Agent produces projected scores for directly affected dimensions
        5. Causal graph propagates effects to dependent dimensions
        6. Compare with current scores
        7. Discard cache
        """
        session = self.sessions.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        current_scenario = self.sessions.load_scenario(session_id)

        logger.info("What-if for %s: %s", session.country_name, question[:100])

        # 1. Create cache session
        cache_id = self.cache.create_session(session_id)

        try:
            # 2. Snapshot KB entries for this country into cache
            query_embedding = embed_texts([question])[0]
            kb_results = self.kb.search(
                query_embedding=query_embedding,
                n_results=20,
            )
            self.cache.populate_from_kb(cache_id, kb_results)

            # If country-specific data exists, add that too
            try:
                country_results = self.kb.search_by_country(
                    query_embedding=query_embedding,
                    country=session.country_name,
                    n_results=10,
                )
                self.cache.populate_from_kb(cache_id, country_results)
            except Exception:
                pass

            # Add hypothetical as a document in the cache
            if hypothetical_changes:
                hyp_text = f"HYPOTHETICAL SCENARIO: {question}\nChanges: {hypothetical_changes}"
                hyp_embedding = embed_texts([hyp_text])[0]
                self.cache.add_hypothetical(
                    cache_id=cache_id,
                    text=hyp_text,
                    embedding=hyp_embedding,
                    metadata={"country": session.country_name, "type": "hypothetical"},
                )

            # 3. Route to agents with cache
            response = self.router.whatif(
                question=question,
                country=session.country_name,
                cache_id=cache_id,
            )

            # 4. Build projected scenario from agent response
            projected = aggregate_agent_responses(
                responses=[response],
                country_name=session.country_name,
                delegate_id=session_id,
                raw_input=question,
            )

            # 5. Determine direct changes and propagate via causal graph
            if current_scenario:
                current_map = {d.dimension_id: d.score for d in current_scenario.dimensions}
                direct_changes: dict[int, float] = {}
                for dim in projected.dimensions:
                    if dim.confidence > 0:
                        old = current_map.get(dim.dimension_id, 0)
                        delta = dim.score - old
                        if abs(delta) > 0.01:
                            direct_changes[dim.dimension_id] = delta

                if direct_changes:
                    # Apply causal propagation to current scores
                    propagated_scores = self.causal.apply_propagation(
                        current_scenario.dimensions,
                        direct_changes,
                    )
                    projected.dimensions = propagated_scores
                    projected.compute_overall()

                # 6. Compare
                comparison = compare_scenarios(current_scenario, projected)
            else:
                comparison = {"note": "No baseline scenario — showing absolute scores"}

            # Build causal effects detail
            causal_effects = {}
            if current_scenario and direct_changes:
                all_effects = self.causal.propagate(direct_changes)
                causal_effects = {
                    str(k): round(v, 3)
                    for k, v in all_effects.items()
                    if k not in direct_changes and abs(v) >= 0.01
                }

        finally:
            # 7. Discard cache
            self.cache.discard_session(cache_id)

        return {
            "question": question,
            "country": session.country_name,
            "projected_summary": scenario_summary(projected),
            "comparison": comparison,
            "causal_effects": causal_effects,
            "agent_narrative": response.narrative,
        }

    # ------------------------------------------------------------------
    # 5. Decision
    # ------------------------------------------------------------------

    def decide(
        self,
        session_id: str,
        decision_text: str,
    ) -> dict[str, Any]:
        """Process a delegate's policy/strategy decision.

        Flow:
        1. Agents validate the decision against current scores
        2. Determine affected dimensions
        3. Record decision in KB (kb_decisions collection)
        4. Recalculate dimension scores
        5. Log to audit trail
        """
        session = self.sessions.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        current_scenario = self.sessions.load_scenario(session_id)
        logger.info("Decision for %s: %s", session.country_name, decision_text[:100])

        # 1. Route to agents for assessment of the decision's impact
        response = self.router.assess(
            f"DECISION IMPACT ASSESSMENT: A delegate from {session.country_name} "
            f"has announced the following decision: '{decision_text}'. "
            f"Assess the impact on all relevant dimensions.",
            session.country_name,
        )

        # 2. Determine affected dimensions
        affected_dims = response.dimensions_assessed

        # 3. Record decision
        decision = DelegateDecision(
            session_id=session_id,
            delegate_id=session_id,
            country_name=session.country_name,
            decision_text=decision_text,
            affected_dimensions=affected_dims,
        )
        record = self.sessions.record_decision(decision)

        # Store in KB decisions collection
        decision_embedding = embed_texts([decision_text])[0]
        self.kb.add_decision(
            decision_text=f"DECISION by {session.country_name}: {decision_text}",
            embedding=decision_embedding,
            metadata={
                "country": session.country_name,
                "session_id": session_id,
                "affected_dimensions": ",".join(str(d) for d in affected_dims),
            },
        )

        # 4. Recalculate scores
        new_scenario = aggregate_agent_responses(
            responses=[response],
            country_name=session.country_name,
            delegate_id=session_id,
            raw_input=decision_text,
        )

        # Apply causal propagation if we have a baseline
        if current_scenario:
            current_map = {d.dimension_id: d.score for d in current_scenario.dimensions}
            changes: dict[int, float] = {}
            for dim in new_scenario.dimensions:
                if dim.confidence > 0:
                    old = current_map.get(dim.dimension_id, 0)
                    delta = dim.score - old
                    if abs(delta) > 0.01:
                        changes[dim.dimension_id] = delta

            if changes:
                propagated = self.causal.apply_propagation(
                    current_scenario.dimensions, changes
                )
                new_scenario.dimensions = propagated
                new_scenario.compute_overall()

            comparison = compare_scenarios(current_scenario, new_scenario)
        else:
            comparison = None

        # 5. Save updated scenario
        self.sessions.save_scenario(session_id, new_scenario)

        return {
            "decision": decision_text,
            "decision_id": record.id,
            "country": session.country_name,
            "affected_dimensions": affected_dims,
            "updated_summary": scenario_summary(new_scenario),
            "comparison": comparison,
            "agent_narrative": response.narrative,
        }

    # ------------------------------------------------------------------
    # Dashboard / Info
    # ------------------------------------------------------------------

    def get_dashboard(self, session_id: str) -> dict[str, Any]:
        """Get the current dashboard for a delegate."""
        session = self.sessions.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        scenario = self.sessions.load_scenario(session_id)
        decisions = self.sessions.get_decisions(session_id=session_id)

        result: dict[str, Any] = {
            "session_id": session_id,
            "country": session.country_name,
            "delegate": session.delegate_name,
        }

        if scenario:
            result["scenario"] = scenario_summary(scenario)
            result["gap_analysis"] = compute_gap_analysis(scenario)
        else:
            result["scenario"] = None
            result["message"] = "No scenario assessed yet. Submit your country data first."

        result["decisions"] = [
            {
                "id": d.id,
                "text": d.decision_text,
                "timestamp": d.timestamp.isoformat(),
                "applied": d.applied,
            }
            for d in decisions
        ]

        return result

    def get_causal_graph(self) -> dict[str, Any]:
        """Return the causal graph structure for visualization."""
        return self.causal.to_dict()

    def get_stats(self) -> dict[str, Any]:
        """Get overall game statistics."""
        return {
            "sessions": self.sessions.stats(),
            "knowledge_base": self.kb.stats(),
            "cache_sessions": self.cache.list_sessions(),
            "causal_graph": {
                "nodes": 13,
                "edges": self.causal.graph.number_of_edges(),
                "most_influential": self.causal.most_influential(5),
            },
        }
