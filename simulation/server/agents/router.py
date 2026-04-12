"""Agent Router — selects and orchestrates agents based on query type and content."""

from __future__ import annotations

import logging
from typing import Any, Optional

from server.agents.base import BaseAgent
from server.agents.dataset import DatasetAgent
from server.agents.opensource import OpenSourceAgent
from server.agents.sandbox import SandboxAgent
from server.agents.research import ResearchAgent
from server.agents.deployment import DeploymentAgent
from server.agents.standards import StandardsAgent
from server.knowledge.kb import KnowledgeBase
from server.knowledge.cache import KnowledgeCache
from server.models import AgentResponse, DimensionScore

logger = logging.getLogger(__name__)

# Dimension -> Agent class mapping
_DIMENSION_AGENT_MAP: dict[int, list[type[BaseAgent]]] = {
    1: [DatasetAgent],
    2: [DatasetAgent, OpenSourceAgent],
    3: [ResearchAgent],
    4: [ResearchAgent],
    5: [OpenSourceAgent, DeploymentAgent],
    6: [StandardsAgent],
    7: [StandardsAgent],
    8: [StandardsAgent],
    9: [ResearchAgent],
    10: [SandboxAgent],
    11: [SandboxAgent],
    12: [DeploymentAgent],
    13: [DeploymentAgent],
}

# Keywords that hint at specific dimensions
_KEYWORD_DIMENSION_HINTS: list[tuple[list[str], list[int]]] = [
    (["data", "dataset", "marketplace", "open data", "data quality"], [1, 2]),
    (["genai", "generated content", "generative", "hallucination"], [2]),
    (["cross-domain", "correlation", "integrated workflow"], [3]),
    (["regional", "local", "indigenous", "contextualization", "customization"], [4]),
    (["workflow", "automation", "integration", "efficiency", "scalability"], [5]),
    (["interface", "chatbot", "language", "usability", "accessibility"], [6]),
    (["strategy", "coordination", "alignment", "intent", "vision"], [7]),
    (["collaboration", "co-creation", "human-ai", "prompting"], [8]),
    (["skills", "training", "talent", "human capital", "awareness"], [9]),
    (["policy", "regulation", "sandbox", "governance", "ethics"], [10]),
    (["inclusion", "digital twin", "edge ai", "sign language", "gender"], [11]),
    (["priority", "fine-tune", "customization", "domain-specific"], [12]),
    (["infrastructure", "5g", "connectivity", "data center", "energy", "compute"], [13]),
]


class AgentRouter:
    """Routes queries to the appropriate agent(s) and merges results."""

    def __init__(
        self,
        kb: KnowledgeBase,
        cache: Optional[KnowledgeCache] = None,
    ):
        self.kb = kb
        self.cache = cache
        self._agent_instances: dict[str, BaseAgent] = {}

    def _get_agent(self, agent_cls: type[BaseAgent]) -> BaseAgent:
        """Get or create a singleton agent instance."""
        name = agent_cls.name
        if name not in self._agent_instances:
            self._agent_instances[name] = agent_cls(kb=self.kb, cache=self.cache)
        return self._agent_instances[name]

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def route(
        self,
        query: str,
        country: Optional[str] = None,
        dimensions: Optional[list[int]] = None,
        interaction_type: str = "clarification",
        cache_id: Optional[str] = None,
    ) -> AgentResponse:
        """Route a query to the appropriate agent(s) and merge responses.

        Parameters
        ----------
        query : str
            The delegate's question or request.
        country : str, optional
            Country context for the query.
        dimensions : list[int], optional
            Explicitly requested dimensions. If None, inferred from query.
        interaction_type : str
            One of: clarification, assessment, whatif, decision
        cache_id : str, optional
            Cache session ID for what-if queries.
        """
        # Determine which dimensions are relevant
        target_dims = dimensions or self._infer_dimensions(query)
        if not target_dims:
            # Default to all dimensions
            target_dims = list(range(1, 14))

        # Find which agent classes to invoke
        agent_classes: set[type[BaseAgent]] = set()
        for dim in target_dims:
            for cls in _DIMENSION_AGENT_MAP.get(dim, []):
                agent_classes.add(cls)

        if not agent_classes:
            # Fallback: use all agents
            agent_classes = {
                DatasetAgent, OpenSourceAgent, SandboxAgent,
                ResearchAgent, DeploymentAgent, StandardsAgent,
            }

        logger.info(
            "Routing query to %d agents for dimensions %s: %s",
            len(agent_classes),
            target_dims,
            [c.name for c in agent_classes],
        )

        # Execute agents and collect responses
        responses: list[AgentResponse] = []
        for agent_cls in agent_classes:
            agent = self._get_agent(agent_cls)
            try:
                if interaction_type == "clarification":
                    resp = agent.clarify(query, country=country)
                elif interaction_type == "whatif" and cache_id:
                    resp = agent.whatif(query, country or "", cache_id)
                elif interaction_type == "assessment":
                    resp = agent.assess(query, country or "")
                else:
                    resp = agent.run(query, country=country, cache_id=cache_id)
                responses.append(resp)
            except Exception as e:
                logger.error("Agent %s failed: %s", agent_cls.name, e)

        # Merge responses
        return self._merge_responses(responses, query, interaction_type)

    def _infer_dimensions(self, query: str) -> list[int]:
        """Infer relevant dimensions from query keywords."""
        query_lower = query.lower()
        dims: set[int] = set()

        for keywords, dim_ids in _KEYWORD_DIMENSION_HINTS:
            for kw in keywords:
                if kw in query_lower:
                    dims.update(dim_ids)
                    break

        return sorted(dims)

    def _merge_responses(
        self,
        responses: list[AgentResponse],
        query: str,
        interaction_type: str = "assessment",
    ) -> AgentResponse:
        """Merge multiple agent responses into a single response.

        For overlapping dimensions, keeps the score with higher confidence.
        Clarifications get longer narratives since they are explanatory.
        """
        if not responses:
            return AgentResponse(
                agent_name="router",
                dimensions_assessed=[],
                scores=[],
                narrative="No agents were able to respond to the query.",
                sources_used=[],
            )

        if len(responses) == 1:
            return responses[0]

        # Clarifications get full narratives; assessments are truncated
        max_narrative = 300 if interaction_type == "assessment" else 2500

        # Merge scores — for overlapping dimensions, pick highest confidence
        best_scores: dict[int, DimensionScore] = {}
        all_dims: set[int] = set()
        all_sources: set[str] = set()
        narratives: list[str] = []

        for resp in responses:
            all_dims.update(resp.dimensions_assessed)
            all_sources.update(resp.sources_used)
            if resp.narrative:
                narratives.append(resp.narrative[:max_narrative])

            for score in resp.scores:
                dim_id = score.dimension_id
                if dim_id not in best_scores or score.confidence > best_scores[dim_id].confidence:
                    best_scores[dim_id] = score

        # For clarifications and what-if, pick the best (longest) narrative
        # For assessments, join all agent narratives
        if interaction_type in ("clarification", "whatif") and narratives:
            merged_narrative = max(narratives, key=len)
        else:
            merged_narrative = " | ".join(narratives)

        return AgentResponse(
            agent_name="router_merged",
            dimensions_assessed=sorted(all_dims),
            scores=sorted(best_scores.values(), key=lambda s: s.dimension_id),
            narrative=merged_narrative,
            sources_used=sorted(all_sources),
        )

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def clarify(self, question: str, country: Optional[str] = None) -> AgentResponse:
        return self.route(question, country=country, interaction_type="clarification")

    def assess(self, scenario_text: str, country: str) -> AgentResponse:
        return self.route(
            scenario_text, country=country,
            interaction_type="assessment",
            dimensions=list(range(1, 14)),
        )

    def whatif(
        self,
        question: str,
        country: str,
        cache_id: str,
        dimensions: Optional[list[int]] = None,
    ) -> AgentResponse:
        return self.route(
            question, country=country,
            interaction_type="whatif",
            cache_id=cache_id,
            dimensions=dimensions,
        )

    def list_agents(self) -> list[dict[str, Any]]:
        """List all available agents and their dimension coverage."""
        agents = [
            DatasetAgent, OpenSourceAgent, SandboxAgent,
            ResearchAgent, DeploymentAgent, StandardsAgent,
        ]
        return [
            {
                "name": a.name,
                "description": a.description,
                "dimensions": a.dimensions,
            }
            for a in agents
        ]
