from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EntityStateRow(Base):
    __tablename__ = "entity_state"

    entity_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    entity_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EntityRevisionRow(Base):
    __tablename__ = "entity_revision"
    __table_args__ = (UniqueConstraint("entity_id", "revision"),)

    revision_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    entity_id: Mapped[str] = mapped_column(
        ForeignKey("entity_state.entity_id", ondelete="RESTRICT"), nullable=False
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)


class DomainEventRow(Base):
    __tablename__ = "domain_event"

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    command_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IdempotencyRecordRow(Base):
    __tablename__ = "idempotency_record"

    idempotency_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    command_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OutboxMessageRow(Base):
    __tablename__ = "outbox_message"

    message_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    event_id: Mapped[str] = mapped_column(
        ForeignKey("domain_event.event_id", ondelete="RESTRICT"), nullable=False
    )
    destination: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MigrationMismatchRow(Base):
    __tablename__ = "migration_mismatch"

    mismatch_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    legacy_key: Mapped[str | None] = mapped_column(String(512))
    candidate_core_identity: Mapped[str | None] = mapped_column(String(128))
    mismatch: Mapped[str] = mapped_column(Text, nullable=False)
    disposition: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)


class WatchlistItemRow(Base):
    __tablename__ = "watchlist_item"
    __table_args__ = (UniqueConstraint("job_id", "job_revision"),)

    watchlist_item_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    job_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    added_by: Mapped[str] = mapped_column(String(32), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OpportunityAdmissionProposalRow(Base):
    __tablename__ = "opportunity_admission_proposal"

    proposal_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    job_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    proposed_by: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OpportunityRecordRow(Base):
    __tablename__ = "opportunity_record"
    __table_args__ = (UniqueConstraint("job_id", "job_revision"),)

    opportunity_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    job_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    admitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    admitted_by: Mapped[str] = mapped_column(String(32), nullable=False)


class OpportunityAdmissionDecisionRow(Base):
    __tablename__ = "opportunity_admission_decision"
    __table_args__ = (
        CheckConstraint("decided_by = 'user'", name="ck_opportunity_decision_user"),
        CheckConstraint(
            "(path = 'proposal' AND proposal_id IS NOT NULL) "
            "OR (path = 'manual' AND proposal_id IS NULL)",
            name="ck_opportunity_decision_path",
        ),
        CheckConstraint(
            "(decision = 'admitted' AND opportunity_id IS NOT NULL) "
            "OR (decision = 'rejected' AND opportunity_id IS NULL)",
            name="ck_opportunity_decision_result",
        ),
        CheckConstraint(
            "path != 'manual' OR decision = 'admitted'",
            name="ck_opportunity_manual_admission",
        ),
    )

    decision_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    job_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    path: Mapped[str] = mapped_column(String(32), nullable=False)
    decided_by: Mapped[str] = mapped_column(String(32), nullable=False)
    proposal_id: Mapped[str | None] = mapped_column(
        ForeignKey("opportunity_admission_proposal.proposal_id", ondelete="RESTRICT")
    )
    opportunity_id: Mapped[str | None] = mapped_column(
        ForeignKey("opportunity_record.opportunity_id", ondelete="RESTRICT")
    )
    reason: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SuggestedPriorityRow(Base):
    __tablename__ = "suggested_priority"
    __table_args__ = (
        CheckConstraint(
            "level IN ('low', 'medium', 'high', 'urgent')",
            name="ck_suggested_priority_level",
        ),
        CheckConstraint("score IS NULL OR (score >= 0 AND score <= 1)", name="ck_priority_score"),
        CheckConstraint("rank IS NULL OR rank >= 1", name="ck_priority_rank"),
    )

    opportunity_id: Mapped[str] = mapped_column(
        ForeignKey("opportunity_record.opportunity_id", ondelete="RESTRICT"), primary_key=True
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    rank: Mapped[int | None] = mapped_column(Integer)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    input_revisions: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserPriorityRow(Base):
    __tablename__ = "user_priority"
    __table_args__ = (
        CheckConstraint(
            "level IN ('low', 'medium', 'high', 'urgent')",
            name="ck_user_priority_level",
        ),
        CheckConstraint("actor = 'user'", name="ck_user_priority_actor"),
    )

    opportunity_id: Mapped[str] = mapped_column(
        ForeignKey("opportunity_record.opportunity_id", ondelete="RESTRICT"), primary_key=True
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(32), nullable=False)
    set_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)

