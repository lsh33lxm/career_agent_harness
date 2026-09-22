"""Persist bounded, reviewable text interview session events."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032_interview_session_events"
down_revision: str | None = "0031_communication_drafts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "interview_session_event",
        sa.Column("event_id", sa.String(128), primary_key=True),
        sa.Column("interview_id", sa.String(128), nullable=False),
        sa.Column("session_id", sa.String(128), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.String(20000), nullable=False),
        sa.Column("source_refs", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "sequence", name="uq_interview_session_sequence"),
        sa.CheckConstraint("role IN ('user','assistant','system')", name="ck_interview_event_role"),
        sa.CheckConstraint("length(content) > 0 AND length(content) <= 20000", name="ck_interview_event_content"),
        sa.CheckConstraint("json_type(source_refs) = 'array'", name="ck_interview_event_refs"),
        sa.Index("ix_interview_session_event_session", "session_id", "sequence"),
    )


def downgrade() -> None:
    op.drop_table("interview_session_event")
