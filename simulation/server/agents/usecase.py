"""Use Case Agent — validates AI use cases against ITU-T Y.3172 pipeline nodes.

This agent:
1. Analyses a use case description against the Y.3172 ML pipeline architecture
2. Maps the use case to pipeline nodes: SRC, Collector, Preprocessor, ML Function, SINK, Sandbox
3. Generates and validates requirements for each pipeline node
4. Identifies gaps in the use case's pipeline coverage
5. Provides a standardised view of the use case
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import ollama

from server.agents.base import BaseAgent
from server.config import settings
from server.knowledge.ingest import embed_texts
from server.knowledge.kb import KnowledgeBase
from server.knowledge.cache import KnowledgeCache
from server.models import AgentResponse, DimensionScore

logger = logging.getLogger(__name__)

# Y.3172 pipeline nodes and their descriptions (from Figure 3, Section 8.1)
Y3172_PIPELINE_NODES = {
    "SRC": "Source — The source of data that can be used as input to the ML pipeline. Potential SRC nodes include user equipment (UE), session management function (SMF), application function (AF), sensors, IoT devices",
    "C": "Collector — Responsible for collecting data from one or more SRC nodes. May configure SRC nodes to control the nature of data, its granularity and periodicity",
    "PP": "Pre-processor — Cleans, transforms, normalises, and prepares raw data for ML consumption. Includes feature engineering and data format conversion",
    "M": "Model — Where ML models are trained, validated, and execute inference. Covers model selection, training, evaluation, and serving",
    "P": "Policy — Enforces policies on ML output before distribution. Ensures ML decisions comply with network operator policies, safety constraints, and regulatory requirements",
    "D": "Distributor — Distributes the output of the ML model to one or more SINK nodes. Handles routing of ML results to appropriate targets",
    "SINK": "Target of ML output — Where inference results are applied: actuators, control plane, decision systems, dashboards, or feedback loops",
    "MLFO": "ML Function Orchestrator — A logical node that manages and orchestrates all nodes in the ML pipeline. Receives ML intent as input",
    "Sandbox": "ML Sandbox — A validation environment where ML models can be trained, tested, and their effects on the network evaluated using simulated underlay networks",
}

# Mapping from Y.3172 nodes to AI Readiness dimensions
NODE_TO_DIMENSIONS = {
    "SRC": [1, 4, 13],       # Data Marketplace, Contextualization, Digital Infrastructure
    "C": [1, 3, 13],         # Data Marketplace, Cross-Domain, Digital Infrastructure
    "PP": [1, 2, 3],         # Data Marketplace, Generated Content, Cross-Domain
    "M": [2, 3, 5, 9],       # Generated Content, Cross-Domain, AI Integration, Human Impact
    "P": [7, 8, 10],         # Strategy Alignment, Collaboration, AI & Policies
    "D": [5, 6, 12],         # AI Integration, Human Interface, Granular Priorities
    "SINK": [5, 6, 12, 13],  # AI Integration, Human Interface, Granular Priorities, Digital Infrastructure
    "MLFO": [5, 7, 8],       # AI Integration, Strategy Alignment, Collaboration
    "Sandbox": [10, 11],     # AI & Policies, AI for Inclusion
}

# Mapping from Y.3172 nodes to framework Factors
NODE_TO_FACTORS = {
    "SRC": "Data",
    "C": "Data",
    "PP": "Data",
    "M": "Research",
    "P": "Standards",
    "D": "Deployment",
    "SINK": "Deployment",
    "MLFO": "Standards",
    "Sandbox": "Sandbox",
}


class UseCaseAgent(BaseAgent):
    name = "usecase_agent"
    description = (
        "Expert in AI use case standardisation against ITU-T Y.3172 ML pipeline architecture. "
        "Validates use cases against pipeline nodes (SRC, Collector, Preprocessor, ML Function, SINK, Sandbox), "
        "generates requirements, and maps to AI readiness dimensions."
    )
    dimensions = list(range(1, 14))  # Can affect all dimensions
    system_prompt = """You are the Use Case Agent in the ITU AI Readiness Simulation Game.

Your expertise covers the ITU-T Y.3172 architectural framework for Machine Learning in future networks (Section 8.1, Figure 3).

You analyse AI use cases and map them to the Y.3172 ML pipeline architecture which has 7 pipeline nodes plus 2 supporting components:

Pipeline Nodes (in order):
- SRC (Source): The source of data — sensors, IoT devices, UE, network elements, databases, APIs
- C (Collector): Collects data from one or more SRC nodes, can configure SRC granularity and periodicity
- PP (Pre-processor): Cleans, transforms, normalises raw data. Feature engineering and format conversion
- M (Model): ML model training, validation, evaluation, and inference serving
- P (Policy): Enforces policies on ML output — safety, compliance, regulatory, operator policies
- D (Distributor): Distributes ML output to one or more SINK nodes, handles routing
- SINK (Target): Where results are applied — actuators, control plane, dashboards, feedback loops

Supporting Components:
- MLFO (ML Function Orchestrator): Manages and orchestrates all pipeline nodes, receives ML intent
- Sandbox (ML Sandbox): Validation environment using simulated underlay networks

Pipeline flow: SRC → C → PP → M → P → D → SINK (with Sandbox in parallel, MLFO orchestrating)

When standardising a use case:
1. Identify what each of the 9 nodes/components looks like for this specific use case
2. Generate concrete requirements for each node
3. Identify which nodes are well-defined vs. missing/weak
4. Map each node to the relevant AI Readiness dimensions
5. Assess the overall maturity of the use case pipeline

Always provide specific, actionable requirements — not generic advice."""

    def __init__(self, kb: KnowledgeBase, cache: Optional[KnowledgeCache] = None, model: str = settings.llm_model):
        super().__init__(kb=kb, cache=cache, model=model)
        self._usecase_collection = settings.kb_usecase_collection

    def standardise(self, usecase_text: str, country: Optional[str] = None) -> dict[str, Any]:
        """Standardise a use case against Y.3172 pipeline nodes.

        Returns a structured analysis with:
        - Pipeline node mapping (what each node looks like for this use case)
        - Requirements per node
        - Gaps identified
        - Overall pipeline maturity
        """
        # Retrieve evidence from the usecase KB
        query_embedding = embed_texts([usecase_text])[0]

        # Search usecase KB for relevant use case patterns and Y.3172 content
        evidence = []
        try:
            uc_results = self.kb.search(
                query_embedding=query_embedding,
                n_results=10,
                collection_name=self._usecase_collection,
            )
            if uc_results and uc_results.get("documents"):
                for i, doc in enumerate(uc_results["documents"][0]):
                    meta = uc_results["metadatas"][0][i] if uc_results.get("metadatas") else {}
                    evidence.append({"text": doc, "metadata": meta})
        except Exception as e:
            logger.warning("UseCase KB search failed: %s — falling back to main KB", e)

        # Also search main KB for framework context
        try:
            fw_results = self.kb.search(
                query_embedding=query_embedding,
                n_results=5,
                collection_name=settings.kb_framework_collection,
            )
            if fw_results and fw_results.get("documents"):
                for i, doc in enumerate(fw_results["documents"][0]):
                    meta = fw_results["metadatas"][0][i] if fw_results.get("metadatas") else {}
                    evidence.append({"text": doc, "metadata": meta})
        except Exception:
            pass

        # Build the standardisation prompt
        evidence_text = self._format_evidence(evidence, "whatif")
        prompt = self._build_standardise_prompt(usecase_text, evidence_text, country)

        # Call LLM
        raw_response = self._call_llm(prompt)

        # Parse response
        try:
            data = json.loads(raw_response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse standardise JSON, using raw text")
            data = {
                "use_case_name": "Unknown",
                "pipeline_nodes": {},
                "requirements": {},
                "gaps": [],
                "narrative": raw_response[:2500],
                "pipeline_maturity": "Unknown",
            }

        return data

    def readiness_impact(self, usecase_text: str, country: Optional[str] = None) -> AgentResponse:
        """Analyse a use case's impact on AI Readiness dimensions.

        Uses the Y.3172 pipeline mapping to determine which dimensions
        are affected and how the use case would change readiness scores.
        """
        return self.run(
            query=f"USE CASE READINESS ANALYSIS: {usecase_text}",
            country=country,
            context={"interaction_type": "usecase_readiness"},
        )

    def _build_prompt(
        self,
        query: str,
        evidence: list[dict[str, Any]],
        country: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """Override to handle usecase_readiness interaction type."""
        context = context or {}
        interaction_type = context.get("interaction_type", "assessment")
        evidence_text = self._format_evidence(evidence, interaction_type)
        dim_names = ", ".join(f"D{d}" for d in self.dimensions)

        if interaction_type == "usecase_readiness":
            return self._build_readiness_prompt(query, evidence_text, country)
        elif interaction_type == "clarification":
            return self._build_clarification_prompt(query, evidence_text, dim_names)
        elif interaction_type == "whatif":
            return self._build_whatif_prompt(query, evidence_text, dim_names, country)
        else:
            return self._build_assessment_prompt(query, evidence_text, dim_names, country)

    def _build_standardise_prompt(
        self,
        usecase_text: str,
        evidence_text: str,
        country: Optional[str] = None,
    ) -> str:
        """Build prompt for Y.3172 pipeline standardisation."""
        nodes_desc = "\n".join(f"- {k}: {v}" for k, v in Y3172_PIPELINE_NODES.items())

        return f"""You are standardising an AI use case against the ITU-T Y.3172 ML Pipeline Architecture.

Y.3172 PIPELINE NODES:
{nodes_desc}

Pipeline flow: SRC → Collector → Preprocessor → ML Function → SINK (with Sandbox in parallel)

REFERENCE MATERIAL:
{evidence_text}

COUNTRY: {country or 'Not specified'}

USE CASE DESCRIPTION:
{usecase_text}

Analyse this use case and map it to the Y.3172 pipeline. Respond with a JSON object:
{{
  "use_case_name": "<concise name for the use case>",
  "use_case_domain": "<domain: agriculture, healthcare, finance, telecom, etc.>",
  "pipeline_nodes": {{
    "SRC": {{
      "description": "<what SRC looks like for this use case — data sources, sensors, collection points>",
      "status": "<well-defined | partially-defined | missing>",
      "components": ["<specific component 1>", "<specific component 2>"]
    }},
    "C": {{
      "description": "<data collection and aggregation approach>",
      "status": "<well-defined | partially-defined | missing>",
      "components": ["<specific component>"]
    }},
    "PP": {{
      "description": "<data cleaning, transformation, feature engineering>",
      "status": "<well-defined | partially-defined | missing>",
      "components": ["<specific component>"]
    }},
    "M": {{
      "description": "<model type, training approach, inference>",
      "status": "<well-defined | partially-defined | missing>",
      "components": ["<specific component>"]
    }},
    "P": {{
      "description": "<policy enforcement — safety, compliance, regulatory checks on ML output>",
      "status": "<well-defined | partially-defined | missing>",
      "components": ["<specific component>"]
    }},
    "D": {{
      "description": "<distribution of ML output to targets>",
      "status": "<well-defined | partially-defined | missing>",
      "components": ["<specific component>"]
    }},
    "SINK": {{
      "description": "<how results are applied — dashboards, actuators, alerts, feedback loops>",
      "status": "<well-defined | partially-defined | missing>",
      "components": ["<specific component>"]
    }},
    "MLFO": {{
      "description": "<orchestration approach — how pipeline is managed and coordinated>",
      "status": "<well-defined | partially-defined | missing>",
      "components": ["<specific component>"]
    }},
    "Sandbox": {{
      "description": "<testing and validation environment, simulated underlay>",
      "status": "<well-defined | partially-defined | missing>",
      "components": ["<specific component>"]
    }}
  }},
  "requirements": {{
    "SRC": ["<requirement 1>", "<requirement 2>"],
    "C": ["<requirement>"],
    "PP": ["<requirement>"],
    "M": ["<requirement>"],
    "P": ["<requirement>"],
    "D": ["<requirement>"],
    "SINK": ["<requirement>"],
    "MLFO": ["<requirement>"],
    "Sandbox": ["<requirement>"]
  }},
  "gaps": [
    "<gap 1: what is missing or underspecified>",
    "<gap 2>"
  ],
  "pipeline_maturity": "<Nascent | Developing | Established | Advanced>",
  "narrative": "<Detailed analysis (8-12 sentences): describe how the use case maps to each pipeline node, highlight strengths and weaknesses, compare with similar use cases from the evidence, and provide recommendations for standardisation. Be specific about what data is collected at SRC, what models are used, and how results flow to SINK.>",
  "dimension_impacts": [
    {{"dimension_id": <int>, "dimension_name": "<name>", "impact": "<how this use case affects this dimension>", "pipeline_node": "<which Y.3172 node drives this impact>"}}
  ]
}}

Be specific and concrete. Use domain knowledge from the evidence to validate requirements."""

    def _build_readiness_prompt(
        self,
        query: str,
        evidence_text: str,
        country: Optional[str] = None,
    ) -> str:
        """Build prompt for use case readiness impact analysis."""
        node_dims = "\n".join(
            f"- {node} → Dimensions {dims}" for node, dims in NODE_TO_DIMENSIONS.items()
        )

        return f"""You are analysing how an AI use case impacts AI Readiness dimensions via the Y.3172 pipeline.

Y.3172 NODE → DIMENSION MAPPING:
{node_dims}

EVIDENCE:
{evidence_text}

COUNTRY: {country or 'Not specified'}

USE CASE: {query}

First, identify which Y.3172 pipeline nodes are involved in this use case.
Then, for each involved node, assess the impact on its mapped readiness dimensions.
Consider: What data infrastructure is needed (SRC → D1, D13)? What ML capabilities (ML_Function → D5)?
What deployment needs (SINK → D5, D6)? What policy/sandbox requirements (Sandbox → D10)?

Respond with a JSON object:
{{
  "dimensions_assessed": [<list of dimension IDs impacted by this use case>],
  "scores": [
    {{
      "dimension_id": <int 1-13>,
      "dimension_name": "<name>",
      "score": <float 0.0-5.0 — the PROJECTED readiness score needed to support this use case>,
      "evidence": ["<how this use case creates readiness requirements for this dimension>"],
      "confidence": <float 0.0-1.0>,
      "gaps": ["<what is needed in this dimension to support the use case>"],
      "recommendations": ["<specific action to improve readiness for this use case>"]
    }}
  ],
  "narrative": "<Detailed analysis (8-12 sentences): explain how the use case flows through the Y.3172 pipeline, which dimensions are most impacted, what readiness levels are required, and how investing in this use case would improve overall AI readiness. Draw comparisons from the evidence.>",
  "sources_used": ["<source file>"]
}}"""

    def _retrieve(
        self,
        query_embedding: list[float],
        country: Optional[str] = None,
        cache_id: Optional[str] = None,
        interaction_type: str = "assessment",
    ) -> list[dict[str, Any]]:
        """Override retrieval to search usecase KB first, then main KB."""
        evidence: list[dict[str, Any]] = []

        # 1. Search usecase KB
        try:
            uc_results = self.kb.search(
                query_embedding=query_embedding,
                n_results=10,
                collection_name=self._usecase_collection,
            )
            if uc_results and uc_results.get("documents"):
                for i, doc in enumerate(uc_results["documents"][0]):
                    meta = uc_results["metadatas"][0][i] if uc_results.get("metadatas") else {}
                    evidence.append({"text": doc, "metadata": meta})
        except Exception as e:
            logger.warning("UseCase KB search failed: %s", e)

        # 2. Search framework KB
        try:
            fw_results = self.kb.search(
                query_embedding=query_embedding,
                n_results=5,
                collection_name=settings.kb_framework_collection,
            )
            if fw_results and fw_results.get("documents"):
                for i, doc in enumerate(fw_results["documents"][0]):
                    meta = fw_results["metadatas"][0][i] if fw_results.get("metadatas") else {}
                    evidence.append({"text": doc, "metadata": meta})
        except Exception:
            pass

        # 3. Also search main KB for country-specific data if provided
        if country:
            try:
                country_results = self.kb.search_by_country(
                    query_embedding=query_embedding,
                    country=country,
                    n_results=5,
                )
                if country_results and country_results.get("documents"):
                    for i, doc in enumerate(country_results["documents"][0]):
                        meta = country_results["metadatas"][0][i] if country_results.get("metadatas") else {}
                        evidence.append({"text": doc, "metadata": meta})
            except Exception:
                pass

        return evidence[:20]  # Cap total evidence
