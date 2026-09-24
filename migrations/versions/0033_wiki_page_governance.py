"""Add review-gated Wiki page metadata and structural operations."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033_wiki_page_governance"
down_revision: str | None = "0032_interview_session_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wiki_page_metadata",
        sa.Column("knowledge_id", sa.String(128), primary_key=True),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("parent_knowledge_id", sa.String(128)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["knowledge_id"], ["knowledge_entry.knowledge_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["parent_knowledge_id"], ["knowledge_entry.knowledge_id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("slug", name="uq_wiki_page_metadata_slug"),
        sa.CheckConstraint("length(trim(slug)) > 0", name="ck_wiki_page_metadata_slug"),
        sa.CheckConstraint(
            "parent_knowledge_id IS NULL OR parent_knowledge_id <> knowledge_id",
            name="ck_wiki_page_metadata_parent",
        ),
    )
    op.create_index(
        "ix_wiki_page_metadata_parent", "wiki_page_metadata", ["parent_knowledge_id"]
    )
    op.create_table(
        "wiki_operation_proposal",
        sa.Column("operation_id", sa.String(128), primary_key=True),
        sa.Column("target_knowledge_id", sa.String(128), nullable=False),
        sa.Column("operation", sa.String(32), nullable=False),
        sa.Column("new_title", sa.String(512)),
        sa.Column("new_slug", sa.String(255)),
        sa.Column("parent_knowledge_id", sa.String(128)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("requested_by", sa.String(255), nullable=False),
        sa.Column("reviewed_by", sa.String(255)),
        sa.Column("review_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["target_knowledge_id"], ["knowledge_entry.knowledge_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["parent_knowledge_id"], ["knowledge_entry.knowledge_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "operation IN ('move', 'rename', 'archive')", name="ck_wiki_operation_kind"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')", name="ck_wiki_operation_status"
        ),
        sa.CheckConstraint(
            "operation <> 'rename' OR new_title IS NOT NULL OR new_slug IS NOT NULL",
            name="ck_wiki_rename_payload",
        ),
        sa.CheckConstraint(
            "operation <> 'move' OR parent_knowledge_id IS NOT NULL",
            name="ck_wiki_move_payload",
        ),
    )
    op.create_index(
        "ix_wiki_operation_target", "wiki_operation_proposal", ["target_knowledge_id", "status"]
    )


def downgrade() -> None:
    op.drop_index("ix_wiki_operation_target", table_name="wiki_operation_proposal")
    op.drop_table("wiki_operation_proposal")
    op.drop_index("ix_wiki_page_metadata_parent", table_name="wiki_page_metadata")
    op.drop_table("wiki_page_metadata")
