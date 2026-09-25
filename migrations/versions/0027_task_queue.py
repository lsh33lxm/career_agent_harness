"""Add durable, version-guarded local task queue."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027_task_queue"
down_revision: str | None = "0026_memory_governance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    statuses = (
        "'pending','processing','completed','failed','cancelled','retrying',"
        "'finalizing','dead_letter'"
    )
    op.create_table(
        "task_queue",
        sa.Column("task_id", sa.String(128), primary_key=True),
        sa.Column("task_type", sa.String(128), nullable=False),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON()),
        sa.Column("last_error", sa.Text()),
        sa.Column("current_attempt", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(f"status IN ({statuses})", name="ck_task_queue_status"),
        sa.CheckConstraint("progress >= 0 AND progress <= 1", name="ck_task_queue_progress"),
        sa.CheckConstraint("current_attempt >= 0", name="ck_task_queue_attempt"),
        sa.CheckConstraint("max_attempts >= 1", name="ck_task_queue_max_attempts"),
        sa.CheckConstraint("version >= 1", name="ck_task_queue_version"),
        sa.CheckConstraint("json_type(payload) = 'object'", name="ck_task_queue_payload"),
        sa.CheckConstraint(
            "result IS NULL OR json_type(result) = 'object'", name="ck_task_queue_result"
        ),
    )
    op.create_index(
        "ix_task_queue_ready", "task_queue", ["stage", "status", "available_at", "created_at"]
    )
    op.create_table(
        "task_attempt",
        sa.Column("task_id", sa.String(128), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("task_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error_type", sa.String(128)),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["task_queue.task_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("task_id", "attempt"),
        sa.CheckConstraint("attempt >= 1", name="ck_task_attempt_number"),
        sa.CheckConstraint("task_version >= 1", name="ck_task_attempt_version"),
        sa.CheckConstraint(
            "status IN ('completed','failed','cancelled','stale')", name="ck_task_attempt_status"
        ),
    )
    op.execute(
        "CREATE TRIGGER trg_task_attempt_no_update BEFORE UPDATE ON task_attempt BEGIN "
        "SELECT RAISE(ABORT, 'task attempts are immutable'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_task_attempt_no_delete BEFORE DELETE ON task_attempt BEGIN "
        "SELECT RAISE(ABORT, 'task attempts are immutable'); END"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_task_attempt_no_delete")
    op.execute("DROP TRIGGER trg_task_attempt_no_update")
    op.drop_table("task_attempt")
    op.drop_index("ix_task_queue_ready", table_name="task_queue")
    op.drop_table("task_queue")
