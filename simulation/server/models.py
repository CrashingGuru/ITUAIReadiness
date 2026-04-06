"""Data models for the AI Readiness Simulation Game."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlmodel import Field as SQLField, SQLModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Factor(str, Enum):
    DATA = "data"
    RESEARCH = "research"
    DEPLOYMENT = "deployment"
    STANDARDS = "standards"
    OPENSOURCE = "opensource"
    SANDBOX = "sandbox"


class InputMethod(str, Enum):
    QUESTIONNAIRE = "questionnaire"
    DOCUMENT = "document"
    NARRATIVE = "narrative"


class InteractionType(str, Enum):
    CLARIFICATION = "clarification"
    WHATIF = "whatif"
    DECISION = "decision"


class SourceType(str, Enum):
    INTERNATIONAL_ORG_REPORT = "international_org_report"
    NATIONAL_STRATEGY = "national_strategy"
    DATASET_CATALOG = "dataset_catalog"
    STANDARDS_DOCUMENT = "standards_document"
    POLICY_DOCUMENT = "policy_document"
    RESEARCH_PAPER = "research_paper"
    DEPLOYMENT_CASE_STUDY = "deployment_case_study"


# ---------------------------------------------------------------------------
# Dimension & Metric definitions (Pydantic, read-only reference data)
# ---------------------------------------------------------------------------

class MetricDefinition(BaseModel):
    """A single metric under a dimension."""
    id: str
    name: str
    description: str
    unit: Optional[str] = None
    example: Optional[str] = None


class DimensionDefinition(BaseModel):
    """One of the 13 AI Readiness dimensions."""
    id: int = Field(ge=1, le=13)
    name: str
    short_name: str
    description: str
    mapped_factors: list[Factor]
    metrics: list[MetricDefinition]


# ---------------------------------------------------------------------------
# Scoring models (Pydantic, used in API requests/responses)
# ---------------------------------------------------------------------------

class DimensionScore(BaseModel):
    """Score for a single dimension in a country scenario."""
    dimension_id: int = Field(ge=1, le=13)
    dimension_name: str
    score: float = Field(ge=0.0, le=5.0)
    evidence: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    gaps: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class CountryScenario(BaseModel):
    """Complete scenario for a country delegate."""
    country_name: str
    delegate_id: str
    dimensions: list[DimensionScore] = Field(default_factory=list)
    raw_input: str = ""
    input_method: InputMethod = InputMethod.NARRATIVE
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    overall_score: Optional[float] = None

    def compute_overall(self) -> float:
        if not self.dimensions:
            return 0.0
        self.overall_score = sum(d.score for d in self.dimensions) / len(self.dimensions)
        return self.overall_score


# ---------------------------------------------------------------------------
# Agent output models
# ---------------------------------------------------------------------------

class AgentResponse(BaseModel):
    """Structured response from an agent."""
    agent_name: str
    dimensions_assessed: list[int]
    scores: list[DimensionScore]
    narrative: str
    sources_used: list[str] = Field(default_factory=list)
    reasoning_chain: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# What-If models
# ---------------------------------------------------------------------------

class WhatIfQuery(BaseModel):
    """A what-if question from a delegate."""
    session_id: str
    delegate_id: str
    question: str
    hypothetical_changes: dict[str, Any] = Field(default_factory=dict)


class WhatIfResult(BaseModel):
    """Result of a what-if analysis."""
    query: WhatIfQuery
    original_scores: list[DimensionScore]
    projected_scores: list[DimensionScore]
    causal_effects: dict[str, float] = Field(default_factory=dict)
    narrative: str
    cache_id: str


# ---------------------------------------------------------------------------
# Decision model
# ---------------------------------------------------------------------------

class DelegateDecision(BaseModel):
    """A policy/strategy decision announced by a delegate."""
    session_id: str
    delegate_id: str
    country_name: str
    decision_text: str
    affected_dimensions: list[int] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# API request/response models
# ---------------------------------------------------------------------------

class RegisterDelegateRequest(BaseModel):
    country_name: str
    delegate_name: str


class ClarifyRequest(BaseModel):
    question: str


class ClarifyResponse(BaseModel):
    question: str
    answer: str
    related_dimensions: list[int]
    related_factors: list[Factor]
    sources: list[str]


class ScenarioInputRequest(BaseModel):
    """Input for creating/updating a country scenario."""
    input_text: Optional[str] = None
    input_method: InputMethod = InputMethod.NARRATIVE
    dimension_scores: Optional[dict[int, float]] = None  # manual scores


# ---------------------------------------------------------------------------
# SQLModel tables (persisted to SQLite)
# ---------------------------------------------------------------------------

class DelegateSession(SQLModel, table=True):
    """Active delegate session."""
    id: str = SQLField(default_factory=lambda: str(uuid4()), primary_key=True)
    country_name: str
    delegate_name: str
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
    is_active: bool = True
    scenario_json: Optional[str] = None  # serialized CountryScenario


class AuditLog(SQLModel, table=True):
    """Audit trail for all KB modifications."""
    id: int = SQLField(default=None, primary_key=True)
    timestamp: datetime = SQLField(default_factory=datetime.utcnow)
    action: str  # ingest, update, delete, decision
    user_id: str
    entity_type: str  # kb_record, decision, score
    entity_id: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    source: str
    reason: str = ""


class DecisionRecord(SQLModel, table=True):
    """Persisted delegate decisions."""
    id: str = SQLField(default_factory=lambda: str(uuid4()), primary_key=True)
    session_id: str
    delegate_id: str
    country_name: str
    decision_text: str
    affected_dimensions: str  # comma-separated dim IDs
    timestamp: datetime = SQLField(default_factory=datetime.utcnow)
    applied: bool = False


class DimensionScoreRecord(SQLModel, table=True):
    """Persisted dimension scores per delegate."""
    id: int = SQLField(default=None, primary_key=True)
    session_id: str
    delegate_id: str
    country_name: str
    dimension_id: int
    score: float
    confidence: float
    evidence_json: str = "[]"
    timestamp: datetime = SQLField(default_factory=datetime.utcnow)
