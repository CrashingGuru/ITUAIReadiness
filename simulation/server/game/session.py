"""Session manager — create/join/leave delegate sessions.

Stores per-delegate CountryScenario in SQLite via SQLModel.
Tracks active delegates and handles multi-delegate state.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlmodel import Session, select

from server.database import engine, create_db_and_tables
from server.models import (
    AuditLog,
    CountryScenario,
    DecisionRecord,
    DelegateDecision,
    DelegateSession,
    DimensionScoreRecord,
)

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages delegate sessions and persisted state."""

    def __init__(self):
        create_db_and_tables()

    # ------------------------------------------------------------------
    # Session CRUD
    # ------------------------------------------------------------------

    def create_session(
        self,
        country_name: str,
        delegate_name: str,
    ) -> DelegateSession:
        """Create a new delegate session."""
        session_obj = DelegateSession(
            country_name=country_name,
            delegate_name=delegate_name,
        )
        with Session(engine) as db:
            db.add(session_obj)
            db.commit()
            db.refresh(session_obj)

        self._audit(
            action="create_session",
            user_id=session_obj.id,
            entity_type="session",
            entity_id=session_obj.id,
            source="session_manager",
            new_value=f"{delegate_name} ({country_name})",
        )
        logger.info("Created session %s for %s (%s)", session_obj.id, delegate_name, country_name)
        return session_obj

    def get_session(self, session_id: str) -> Optional[DelegateSession]:
        """Get a session by ID."""
        with Session(engine) as db:
            return db.get(DelegateSession, session_id)

    def get_active_sessions(self) -> list[DelegateSession]:
        """Get all active sessions."""
        with Session(engine) as db:
            stmt = select(DelegateSession).where(DelegateSession.is_active == True)
            return list(db.exec(stmt).all())

    def deactivate_session(self, session_id: str) -> None:
        """Mark a session as inactive (delegate leaves)."""
        with Session(engine) as db:
            session_obj = db.get(DelegateSession, session_id)
            if session_obj:
                session_obj.is_active = False
                db.add(session_obj)
                db.commit()
                logger.info("Deactivated session %s", session_id)

    # ------------------------------------------------------------------
    # Scenario persistence
    # ------------------------------------------------------------------

    def save_scenario(
        self,
        session_id: str,
        scenario: CountryScenario,
    ) -> None:
        """Save/update a delegate's country scenario."""
        with Session(engine) as db:
            session_obj = db.get(DelegateSession, session_id)
            if not session_obj:
                raise ValueError(f"Session {session_id} not found")
            session_obj.scenario_json = scenario.model_dump_json()
            db.add(session_obj)

            # Also persist individual dimension scores
            for dim in scenario.dimensions:
                record = DimensionScoreRecord(
                    session_id=session_id,
                    delegate_id=scenario.delegate_id,
                    country_name=scenario.country_name,
                    dimension_id=dim.dimension_id,
                    score=dim.score,
                    confidence=dim.confidence,
                    evidence_json=json.dumps(dim.evidence),
                )
                db.add(record)

            db.commit()

        self._audit(
            action="save_scenario",
            user_id=scenario.delegate_id,
            entity_type="scenario",
            entity_id=session_id,
            source="session_manager",
            new_value=f"overall={scenario.overall_score:.2f}" if scenario.overall_score else "new",
        )
        logger.info("Saved scenario for session %s (%s)", session_id, scenario.country_name)

    def load_scenario(self, session_id: str) -> Optional[CountryScenario]:
        """Load a delegate's country scenario."""
        with Session(engine) as db:
            session_obj = db.get(DelegateSession, session_id)
            if not session_obj or not session_obj.scenario_json:
                return None
            return CountryScenario.model_validate_json(session_obj.scenario_json)

    # ------------------------------------------------------------------
    # Decision persistence
    # ------------------------------------------------------------------

    def record_decision(self, decision: DelegateDecision) -> DecisionRecord:
        """Persist a delegate decision."""
        record = DecisionRecord(
            session_id=decision.session_id,
            delegate_id=decision.delegate_id,
            country_name=decision.country_name,
            decision_text=decision.decision_text,
            affected_dimensions=",".join(str(d) for d in decision.affected_dimensions),
        )
        with Session(engine) as db:
            db.add(record)
            db.commit()
            db.refresh(record)

        self._audit(
            action="decision",
            user_id=decision.delegate_id,
            entity_type="decision",
            entity_id=record.id,
            source="session_manager",
            new_value=decision.decision_text[:200],
        )
        logger.info("Recorded decision %s for %s", record.id, decision.country_name)
        return record

    def get_decisions(
        self,
        session_id: Optional[str] = None,
        country_name: Optional[str] = None,
    ) -> list[DecisionRecord]:
        """Get decisions filtered by session or country."""
        with Session(engine) as db:
            stmt = select(DecisionRecord)
            if session_id:
                stmt = stmt.where(DecisionRecord.session_id == session_id)
            if country_name:
                stmt = stmt.where(DecisionRecord.country_name == country_name)
            return list(db.exec(stmt.order_by(DecisionRecord.timestamp)).all())

    # ------------------------------------------------------------------
    # Score history
    # ------------------------------------------------------------------

    def get_score_history(
        self,
        session_id: str,
        dimension_id: Optional[int] = None,
    ) -> list[DimensionScoreRecord]:
        """Get score history for a session, optionally filtered by dimension."""
        with Session(engine) as db:
            stmt = select(DimensionScoreRecord).where(
                DimensionScoreRecord.session_id == session_id
            )
            if dimension_id:
                stmt = stmt.where(DimensionScoreRecord.dimension_id == dimension_id)
            return list(db.exec(stmt.order_by(DimensionScoreRecord.timestamp)).all())

    # ------------------------------------------------------------------
    # Audit logging
    # ------------------------------------------------------------------

    def _audit(
        self,
        action: str,
        user_id: str,
        entity_type: str,
        entity_id: str,
        source: str,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        reason: str = "",
    ) -> None:
        """Write an audit log entry."""
        entry = AuditLog(
            action=action,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            source=source,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
        )
        with Session(engine) as db:
            db.add(entry)
            db.commit()

    def get_audit_log(self, limit: int = 50) -> list[AuditLog]:
        """Get recent audit log entries."""
        with Session(engine) as db:
            stmt = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
            return list(db.exec(stmt).all())

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """Get session manager statistics."""
        with Session(engine) as db:
            total = db.exec(select(DelegateSession)).all()
            active = [s for s in total if s.is_active]
            decisions = db.exec(select(DecisionRecord)).all()
            return {
                "total_sessions": len(total),
                "active_sessions": len(active),
                "total_decisions": len(decisions),
                "countries": list(set(s.country_name for s in active)),
            }
