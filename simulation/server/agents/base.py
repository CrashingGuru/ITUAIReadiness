"""Base agent class for AI Readiness Simulation Game.

Wraps Ollama LLM calls with RAG retrieval from the Knowledge Base.
Each specialized agent inherits from this and provides its own
system prompt, dimension coverage, and tools.

We use direct Ollama calls + instructor for structured output rather
than smolagents, to keep the prototype lightweight and avoid litellm
compatibility issues with local Ollama.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import ollama

from server.config import settings
from server.knowledge.kb import KnowledgeBase
from server.knowledge.cache import KnowledgeCache
from server.knowledge.ingest import embed_texts
from server.models import AgentResponse, DimensionScore

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all AI Readiness agents."""

    # Subclasses override these
    name: str = "base_agent"
    description: str = "Base agent"
    dimensions: list[int] = []  # which dimensions this agent covers
    system_prompt: str = "You are an AI Readiness assessment agent."

    def __init__(
        self,
        kb: KnowledgeBase,
        cache: Optional[KnowledgeCache] = None,
        model: str = settings.llm_model,
    ):
        self.kb = kb
        self.cache = cache
        self.model = model
        self._client = ollama.Client(host=settings.ollama_base_url)

    # ------------------------------------------------------------------
    # Core reasoning loop
    # ------------------------------------------------------------------

    def run(
        self,
        query: str,
        country: Optional[str] = None,
        cache_id: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> AgentResponse:
        """Execute the agent reasoning loop.

        1. Embed the query
        2. Retrieve evidence from KB (or Cache if cache_id provided)
        3. Build prompt with evidence
        4. Call LLM for structured reasoning
        5. Parse into AgentResponse
        """
        context = context or {}
        interaction_type = context.get("interaction_type", "assessment")

        # 1. Embed query
        query_embedding = embed_texts([query])[0]

        # 2. Retrieve evidence
        evidence = self._retrieve(query_embedding, country, cache_id, interaction_type)

        # 3. Build prompt
        prompt = self._build_prompt(query, evidence, country, context)

        # 4. Call LLM
        raw_response = self._call_llm(prompt)

        # 5. Parse response
        return self._parse_response(raw_response, evidence)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def _retrieve(
        self,
        query_embedding: list[float],
        country: Optional[str] = None,
        cache_id: Optional[str] = None,
        interaction_type: str = "assessment",
    ) -> list[dict[str, Any]]:
        """Retrieve relevant evidence from KB or Cache.

        Retrieval strategy varies by interaction type:
        - clarification: framework-first (definitions, metrics, mappings)
        - assessment/decision: country + KB evidence
        - whatif: cache-first, then KB as base
        """
        evidence: list[dict[str, Any]] = []

        is_clarification = interaction_type == "clarification"

        # --- Framework definitions (always, but prioritized for clarifications) ---
        fw_results = self.kb.search(
            query_embedding=query_embedding,
            n_results=10 if is_clarification else 3,
            collection_name=settings.kb_framework_collection,
        )
        evidence.extend(self._flatten_results(fw_results, source="kb_framework"))

        # --- For clarifications: lean heavily on framework + ITU source docs ---
        if is_clarification:
            # Search KB for ITU framework document chunks specifically
            try:
                itu_results = self.kb.search_text(
                    query_embedding=query_embedding,
                    contains="Dimension",
                    n_results=5,
                )
                evidence.extend(self._flatten_results(itu_results, source="kb_main"))
            except Exception:
                pass

            # Light broad search for supplementary context
            kb_broad = self.kb.search(
                query_embedding=query_embedding,
                n_results=3,
            )
            evidence.extend(self._flatten_results(kb_broad, source="kb_main"))

            # Skip country-specific and dimension-filtered searches

        else:
            # --- Normal retrieval for assessment/whatif/decision ---

            # Search cache first if in what-if mode
            if cache_id and self.cache and self.cache.is_active(cache_id):
                cache_results = self.cache.search(
                    cache_id=cache_id,
                    query_embedding=query_embedding,
                    n_results=5,
                )
                evidence.extend(self._flatten_results(cache_results, source="cache"))

            # Search KB filtered by dimension
            for dim_id in self.dimensions:
                try:
                    kb_results = self.kb.search_by_dimension(
                        query_embedding=query_embedding,
                        dimension_id=dim_id,
                        n_results=3,
                    )
                    evidence.extend(self._flatten_results(kb_results, source="kb_main"))
                except Exception:
                    pass

            # Unfiltered KB search for broader context
            kb_broad = self.kb.search(
                query_embedding=query_embedding,
                n_results=5,
            )
            evidence.extend(self._flatten_results(kb_broad, source="kb_main"))

            # Country-specific search
            if country:
                try:
                    country_results = self.kb.search_by_country(
                        query_embedding=query_embedding,
                        country=country,
                        n_results=5,
                    )
                    evidence.extend(self._flatten_results(country_results, source="kb_main"))
                except Exception:
                    pass

        # Deduplicate by text content
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for e in evidence:
            text_key = e.get("text", "")[:100]
            if text_key not in seen:
                seen.add(text_key)
                unique.append(e)
        return unique[:20]

    def _flatten_results(
        self,
        results: dict[str, Any],
        source: str = "kb",
    ) -> list[dict[str, Any]]:
        """Convert ChromaDB query results into flat evidence list."""
        evidence = []
        ids = results.get("ids", [[]])
        docs = results.get("documents", [[]])
        metas = results.get("metadatas", [[]])
        dists = results.get("distances", [[]])

        # Handle nested list structure from ChromaDB
        if ids and isinstance(ids[0], list):
            ids, docs, metas, dists = ids[0], docs[0], metas[0], dists[0]

        for i, doc in enumerate(docs):
            evidence.append({
                "text": doc,
                "metadata": metas[i] if i < len(metas) else {},
                "distance": dists[i] if i < len(dists) else None,
                "source": source,
            })
        return evidence

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        query: str,
        evidence: list[dict[str, Any]],
        country: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """Build the full prompt with system prompt, evidence, and query."""
        context = context or {}
        interaction_type = context.get("interaction_type", "assessment")
        evidence_text = self._format_evidence(evidence)
        dim_names = ", ".join(f"D{d}" for d in self.dimensions)

        if interaction_type == "clarification":
            return self._build_clarification_prompt(query, evidence_text, dim_names)
        else:
            return self._build_assessment_prompt(query, evidence_text, dim_names, country)

    def _build_clarification_prompt(
        self,
        query: str,
        evidence_text: str,
        dim_names: str,
    ) -> str:
        """Prompt for clarification queries — explain the framework, not the country."""
        return f"""You are answering a CLARIFICATION question about the ITU AI Readiness Framework.
Your role is to EXPLAIN the framework — its dimensions, metrics, factors, and how they relate.
Do NOT assess or score any country. Focus on explaining concepts, definitions, and mappings.

You are an expert on dimensions: {dim_names}.

FRAMEWORK REFERENCE:
{evidence_text}

QUESTION: {query}

Respond with a JSON object containing:
{{
  "dimensions_assessed": [list of dimension IDs relevant to this question],
  "scores": [],
  "narrative": "<clear explanation answering the question, referencing specific dimensions, metrics, and factors from the framework>",
  "sources_used": ["<source file 1>", "<source file 2>"]
}}

Focus on:
- What the dimension measures and why it matters
- Which metrics fall under it
- Which factors it maps to (data, research, deployment, standards, opensource, sandbox)
- How it relates to other dimensions
- Provide specific examples from the framework evidence above"""

    def _build_assessment_prompt(
        self,
        query: str,
        evidence_text: str,
        dim_names: str,
        country: Optional[str] = None,
    ) -> str:
        """Prompt for assessment, what-if, and decision queries."""
        return f"""Based on the following evidence from the ITU AI Readiness Knowledge Base,
answer the query below. You are responsible for dimensions: {dim_names}.

EVIDENCE:
{evidence_text}

COUNTRY: {country or 'Not specified'}

QUERY: {query}

Respond with a JSON object containing:
{{
  "dimensions_assessed": [list of dimension IDs you assessed],
  "scores": [
    {{
      "dimension_id": <int 1-13>,
      "dimension_name": "<name>",
      "score": <float 0.0-5.0>,
      "evidence": ["<supporting fact 1>", "<supporting fact 2>"],
      "confidence": <float 0.0-1.0>,
      "gaps": ["<gap 1>", "<gap 2>"],
      "recommendations": ["<recommendation 1>"]
    }}
  ],
  "narrative": "<2-3 sentence summary of your assessment>",
  "sources_used": ["<source file 1>", "<source file 2>"]
}}

If you cannot assess a dimension due to insufficient evidence, set its score to -1
and explain in the gaps field. Always provide a narrative summary."""

    def _format_evidence(self, evidence: list[dict[str, Any]]) -> str:
        """Format evidence items into readable text for the prompt."""
        if not evidence:
            return "(No relevant evidence found)"

        parts = []
        for i, e in enumerate(evidence[:8], 1):
            meta = e.get("metadata", {})
            source = meta.get("source_file", "unknown")
            country = meta.get("country", "")
            text = e.get("text", "")[:300]  # truncate to keep prompt compact
            parts.append(f"[{i}] Source: {source} | Country: {country}\n{text}")

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str) -> str:
        """Call the Ollama LLM with system prompt + user prompt."""
        try:
            response = self._client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                options={
                    "temperature": 0.3,
                    "num_predict": 4096,
                    "num_ctx": 8192,
                },
                format="json",
            )
            return response["message"]["content"]
        except Exception as e:
            logger.error("LLM call failed for %s: %s", self.name, e)
            return json.dumps({
                "dimensions_assessed": self.dimensions,
                "scores": [],
                "narrative": f"Agent {self.name} failed to generate response: {e}",
                "sources_used": [],
            })

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response(
        self,
        raw_response: str,
        evidence: list[dict[str, Any]],
    ) -> AgentResponse:
        """Parse LLM JSON response into AgentResponse."""
        try:
            data = json.loads(raw_response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from %s, using raw text", self.name)
            return AgentResponse(
                agent_name=self.name,
                dimensions_assessed=self.dimensions,
                scores=[],
                narrative=raw_response[:500],
                sources_used=[],
            )

        scores = []
        for s in data.get("scores", []):
            try:
                score_val = float(s.get("score", -1))
                if score_val < 0:
                    continue
                scores.append(DimensionScore(
                    dimension_id=int(s.get("dimension_id", 0)),
                    dimension_name=str(s.get("dimension_name", "")),
                    score=min(max(score_val, 0.0), 5.0),
                    evidence=s.get("evidence", []),
                    metrics=s.get("metrics", {}),
                    confidence=float(s.get("confidence", 0.5)),
                    gaps=s.get("gaps", []),
                    recommendations=s.get("recommendations", []),
                ))
            except (ValueError, TypeError) as e:
                logger.warning("Skipping malformed score in %s: %s", self.name, e)

        # Sanitize dimensions_assessed — LLM may return "Dimension 1" instead of 1
        raw_dims = data.get("dimensions_assessed", self.dimensions)
        clean_dims: list[int] = []
        for d in raw_dims:
            if isinstance(d, int):
                clean_dims.append(d)
            elif isinstance(d, str):
                m = re.search(r'\d+', d)
                if m:
                    clean_dims.append(int(m.group()))
            else:
                try:
                    clean_dims.append(int(d))
                except (ValueError, TypeError):
                    pass
        if not clean_dims:
            clean_dims = self.dimensions

        return AgentResponse(
            agent_name=self.name,
            dimensions_assessed=clean_dims,
            scores=scores,
            narrative=data.get("narrative", ""),
            sources_used=data.get("sources_used", []),
            reasoning_chain=data.get("reasoning_chain", []),
        )

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def clarify(self, question: str, country: Optional[str] = None) -> AgentResponse:
        """Answer a clarification question about dimensions/metrics."""
        return self.run(
            query=f"CLARIFICATION REQUEST: {question}",
            country=country,
            context={"interaction_type": "clarification"},
        )

    def assess(self, scenario_text: str, country: str) -> AgentResponse:
        """Assess a country scenario against this agent's dimensions."""
        return self.run(
            query=f"ASSESSMENT REQUEST: Assess the following country scenario for dimensions {self.dimensions}:\n\n{scenario_text}",
            country=country,
            context={"interaction_type": "assessment"},
        )

    def whatif(
        self,
        question: str,
        country: str,
        cache_id: str,
    ) -> AgentResponse:
        """Run a what-if analysis using the Knowledge Cache."""
        return self.run(
            query=f"WHAT-IF ANALYSIS: {question}",
            country=country,
            cache_id=cache_id,
            context={"interaction_type": "whatif"},
        )
