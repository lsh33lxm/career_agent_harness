"""Add versioned official capability graph and personal overlay records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_capability_core"
down_revision: str | None = "0002_opportunity_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "capability_identity",
        sa.Column("capability_id", sa.String(length=128), primary_key=True),
    )
    op.create_table(
        "capability_graph_version",
        sa.Column("graph_version_id", sa.String(length=128), primary_key=True),
        sa.Column("version_label", sa.String(length=64), nullable=False, unique=True),
        sa.Column("parent_graph_version_id", sa.String(length=128)),
        sa.Column("change_note", sa.Text(), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_by", sa.String(length=255), nullable=False),
        sa.Column("released_by_kind", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "parent_graph_version_id IS NULL OR parent_graph_version_id != graph_version_id",
            name="ck_capability_graph_parent_not_self",
        ),
        sa.CheckConstraint(
            "released_by_kind IN ('user', 'rule')",
            name="ck_capability_graph_release_authority",
        ),
        sa.ForeignKeyConstraint(
            ["parent_graph_version_id"],
            ["capability_graph_version.graph_version_id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_table(
        "capability_node",
        sa.Column("capability_id", sa.String(length=128), primary_key=True),
        sa.Column("graph_version_id", sa.String(length=128), primary_key=True),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("layer", sa.String(length=32), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "layer IN ('common_core', 'track', 'opportunity_specific')",
            name="ck_capability_node_layer",
        ),
        sa.CheckConstraint(
            "lifecycle_status IN ('active', 'deprecated', 'retired')",
            name="ck_capability_node_lifecycle",
        ),
        sa.ForeignKeyConstraint(
            ["capability_id"], ["capability_identity.capability_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["graph_version_id"],
            ["capability_graph_version.graph_version_id"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    op.create_table(
        "capability_relation",
        sa.Column("relation_id", sa.String(length=128), primary_key=True),
        sa.Column("source_capability_id", sa.String(length=128), nullable=False),
        sa.Column("target_capability_id", sa.String(length=128), nullable=False),
        sa.Column("relation_type", sa.String(length=32), nullable=False),
        sa.Column("graph_version_id", sa.String(length=128), nullable=False),
        sa.CheckConstraint(
            "source_capability_id != target_capability_id",
            name="ck_capability_relation_distinct_nodes",
        ),
        sa.CheckConstraint(
            "relation_type IN ('prerequisite', 'part_of', 'related_to')",
            name="ck_capability_relation_type",
        ),
        sa.ForeignKeyConstraint(
            ["source_capability_id", "graph_version_id"],
            ["capability_node.capability_id", "capability_node.graph_version_id"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["target_capability_id", "graph_version_id"],
            ["capability_node.capability_id", "capability_node.graph_version_id"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    op.create_table(
        "candidate_capability_node",
        sa.Column("candidate_node_id", sa.String(length=128), primary_key=True),
        sa.Column("proposed_canonical_name", sa.String(length=255), nullable=False),
        sa.Column("proposed_description", sa.Text(), nullable=False),
        sa.Column("proposed_layer", sa.String(length=32), nullable=False),
        sa.Column("source_evidence_refs", sa.JSON(), nullable=False),
        sa.Column("discovered_by", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reviewed_by", sa.String(length=255)),
        sa.Column("reviewed_by_kind", sa.String(length=32)),
        sa.Column("review_reason", sa.Text()),
        sa.Column("merge_target_capability_id", sa.String(length=128)),
        sa.CheckConstraint(
            "proposed_layer IN ('common_core', 'track', 'opportunity_specific')",
            name="ck_candidate_capability_layer",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'merged', 'ignored', 'deferred')",
            name="ck_candidate_capability_status",
        ),
        sa.CheckConstraint(
            "json_type(source_evidence_refs) = 'array' "
            "AND json_array_length(source_evidence_refs) > 0",
            name="ck_candidate_capability_evidence_refs",
        ),
        sa.CheckConstraint(
            "(status = 'pending' AND reviewed_by IS NULL AND reviewed_by_kind IS NULL "
            "AND review_reason IS NULL) OR (status != 'pending' AND reviewed_by IS NOT NULL "
            "AND reviewed_by_kind IN ('user', 'rule') "
            "AND review_reason IS NOT NULL)",
            name="ck_candidate_capability_review",
        ),
        sa.CheckConstraint(
            "(status = 'merged' AND merge_target_capability_id IS NOT NULL) "
            "OR (status != 'merged' AND merge_target_capability_id IS NULL)",
            name="ck_candidate_capability_merge_target",
        ),
        sa.ForeignKeyConstraint(
            ["merge_target_capability_id"],
            ["capability_identity.capability_id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_table(
        "personal_capability_state",
        sa.Column("personal_state_id", sa.String(length=128), primary_key=True),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("capability_id", sa.String(length=128), nullable=False),
        sa.Column("understand", sa.Boolean(), nullable=False),
        sa.Column("explain", sa.Boolean(), nullable=False),
        sa.Column("apply", sa.Boolean(), nullable=False),
        sa.Column("evidence", sa.Boolean(), nullable=False),
        sa.Column("interview_ready", sa.Boolean(), nullable=False),
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.String(length=255), nullable=False),
        sa.Column("updated_by_kind", sa.String(length=32), nullable=False),
        sa.CheckConstraint("revision >= 1", name="ck_personal_capability_revision"),
        sa.CheckConstraint(
            "schema_version >= 1", name="ck_personal_capability_schema_version"
        ),
        sa.CheckConstraint(
            "updated_by_kind IN ('user', 'rule')",
            name="ck_personal_capability_update_authority",
        ),
        sa.ForeignKeyConstraint(
            ["capability_id"], ["capability_identity.capability_id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("personal_state_id", "revision", "capability_id"),
        sa.UniqueConstraint(
            "personal_state_id", "revision", "candidate_id", "capability_id"
        ),
    )
    op.create_index(
        "ix_personal_capability_state_candidate_id",
        "personal_capability_state",
        ["candidate_id"],
    )
    op.create_table(
        "capability_evidence_binding",
        sa.Column("binding_id", sa.String(length=128), primary_key=True),
        sa.Column("personal_state_id", sa.String(length=128), nullable=False),
        sa.Column("personal_state_revision", sa.Integer(), nullable=False),
        sa.Column("capability_id", sa.String(length=128), nullable=False),
        sa.Column("evidence_ref_id", sa.String(length=128)),
        sa.Column("project_evidence_id", sa.String(length=128)),
        sa.Column("authority", sa.String(length=32), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("bound_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bound_by", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "(evidence_ref_id IS NOT NULL AND project_evidence_id IS NULL) "
            "OR (evidence_ref_id IS NULL AND project_evidence_id IS NOT NULL)",
            name="ck_capability_evidence_exactly_one_source",
        ),
        sa.CheckConstraint(
            "authority IN ('code_verified', 'document_supported', 'user_confirmed', "
            "'ai_inferred')",
            name="ck_capability_evidence_authority",
        ),
        sa.CheckConstraint(
            "json_type(scopes) = 'array' AND json_array_length(scopes) > 0",
            name="ck_capability_evidence_scopes",
        ),
        sa.ForeignKeyConstraint(
            ["personal_state_id", "personal_state_revision", "capability_id"],
            [
                "personal_capability_state.personal_state_id",
                "personal_capability_state.revision",
                "personal_capability_state.capability_id",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["capability_id"], ["capability_identity.capability_id"], ondelete="RESTRICT"
        ),
    )
    op.create_table(
        "capability_market_binding",
        sa.Column("binding_id", sa.String(length=128), primary_key=True),
        sa.Column("capability_id", sa.String(length=128), nullable=False),
        sa.Column("market_scope", sa.String(length=32), nullable=False),
        sa.Column("source_evidence_refs", sa.JSON(), nullable=False),
        sa.Column("opportunity_id", sa.String(length=128)),
        sa.Column("job_requirement_id", sa.String(length=128)),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "market_scope IN ('target', 'broad')",
            name="ck_capability_market_scope",
        ),
        sa.CheckConstraint(
            "json_type(source_evidence_refs) = 'array' "
            "AND json_array_length(source_evidence_refs) > 0",
            name="ck_capability_market_evidence_refs",
        ),
        sa.CheckConstraint(
            "(market_scope = 'target' AND "
            "(opportunity_id IS NOT NULL OR job_requirement_id IS NOT NULL)) "
            "OR (market_scope = 'broad' AND opportunity_id IS NULL "
            "AND job_requirement_id IS NULL)",
            name="ck_capability_market_target_refs",
        ),
        sa.ForeignKeyConstraint(
            ["capability_id"], ["capability_identity.capability_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunity_record.opportunity_id"], ondelete="RESTRICT"
        ),
    )
    op.create_table(
        "capability_investment_state",
        sa.Column("investment_state_id", sa.String(length=128), primary_key=True),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("capability_id", sa.String(length=128), nullable=False),
        sa.Column("target_market_demand", sa.Float(), nullable=False),
        sa.Column("opportunity_importance", sa.Float(), nullable=False),
        sa.Column("cross_opportunity_reuse", sa.Float(), nullable=False),
        sa.Column("project_proximity", sa.Float(), nullable=False),
        sa.Column("evidence_feasibility", sa.Float(), nullable=False),
        sa.Column("personal_interest", sa.Float(), nullable=False),
        sa.Column("learning_cost", sa.Float(), nullable=False),
        sa.Column("recommendation", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("graph_version_id", sa.String(length=128), nullable=False),
        sa.Column("personal_state_id", sa.String(length=128), nullable=False),
        sa.Column("personal_state_revision", sa.Integer(), nullable=False),
        sa.Column("market_binding_ids", sa.JSON(), nullable=False),
        sa.Column("opportunity_ids", sa.JSON(), nullable=False),
        sa.Column("rule_version", sa.String(length=64), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "target_market_demand BETWEEN 0 AND 1 "
            "AND opportunity_importance BETWEEN 0 AND 1 "
            "AND cross_opportunity_reuse BETWEEN 0 AND 1 "
            "AND project_proximity BETWEEN 0 AND 1 "
            "AND evidence_feasibility BETWEEN 0 AND 1 "
            "AND personal_interest BETWEEN 0 AND 1 "
            "AND learning_cost BETWEEN 0 AND 1 "
            "AND score BETWEEN 0 AND 1",
            name="ck_capability_investment_unit_interval",
        ),
        sa.CheckConstraint(
            "recommendation IN ('low', 'medium', 'high')",
            name="ck_capability_investment_recommendation",
        ),
        sa.CheckConstraint(
            "(score >= 0.6 AND recommendation = 'high') "
            "OR (score >= 0.35 AND score < 0.6 AND recommendation = 'medium') "
            "OR (score < 0.35 AND recommendation = 'low')",
            name="ck_capability_investment_score_recommendation",
        ),
        sa.CheckConstraint(
            "score = round(max(0.0, min(1.0, "
            "target_market_demand * 0.25 + opportunity_importance * 0.20 "
            "+ cross_opportunity_reuse * 0.20 + project_proximity * 0.10 "
            "+ evidence_feasibility * 0.15 + personal_interest * 0.10 "
            "- learning_cost * 0.25)), 3)",
            name="ck_capability_investment_score_factors",
        ),
        sa.CheckConstraint(
            "rule_version = 'capability-investment-v1'",
            name="ck_capability_investment_rule_version",
        ),
        sa.CheckConstraint(
            "json_type(reasons) = 'array' AND json_array_length(reasons) > 0",
            name="ck_capability_investment_reasons",
        ),
        sa.CheckConstraint(
            "json_type(market_binding_ids) = 'array' "
            "AND json_array_length(market_binding_ids) > 0",
            name="ck_capability_investment_market_bindings",
        ),
        sa.CheckConstraint(
            "personal_state_revision >= 1",
            name="ck_capability_investment_personal_revision",
        ),
        sa.ForeignKeyConstraint(
            ["capability_id"], ["capability_identity.capability_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["graph_version_id"],
            ["capability_graph_version.graph_version_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            [
                "personal_state_id",
                "personal_state_revision",
                "candidate_id",
                "capability_id",
            ],
            [
                "personal_capability_state.personal_state_id",
                "personal_capability_state.revision",
                "personal_capability_state.candidate_id",
                "personal_capability_state.capability_id",
            ],
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_capability_investment_state_candidate_id",
        "capability_investment_state",
        ["candidate_id"],
    )
    op.execute(
        "CREATE TRIGGER trg_capability_graph_version_no_update "
        "BEFORE UPDATE ON capability_graph_version BEGIN "
        "SELECT RAISE(ABORT, 'released capability graph is immutable'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_capability_graph_version_no_delete "
        "BEFORE DELETE ON capability_graph_version BEGIN "
        "SELECT RAISE(ABORT, 'released capability graph is immutable'); END"
    )
    for table_name in ("capability_node", "capability_relation"):
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_append_released "
            f"BEFORE INSERT ON {table_name} WHEN EXISTS ("
            "SELECT 1 FROM capability_graph_version "
            f"WHERE graph_version_id = NEW.graph_version_id) BEGIN "
            "SELECT RAISE(ABORT, 'cannot append to released capability graph'); END"
        )
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_update "
            f"BEFORE UPDATE ON {table_name} BEGIN "
            "SELECT RAISE(ABORT, 'released capability graph is immutable'); END"
        )
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_delete "
            f"BEFORE DELETE ON {table_name} BEGIN "
            "SELECT RAISE(ABORT, 'released capability graph is immutable'); END"
        )


def downgrade() -> None:
    for table_name in ("capability_relation", "capability_node"):
        op.execute(f"DROP TRIGGER trg_{table_name}_no_delete")
        op.execute(f"DROP TRIGGER trg_{table_name}_no_update")
        op.execute(f"DROP TRIGGER trg_{table_name}_no_append_released")
    op.execute("DROP TRIGGER trg_capability_graph_version_no_delete")
    op.execute("DROP TRIGGER trg_capability_graph_version_no_update")
    op.drop_index(
        "ix_capability_investment_state_candidate_id",
        table_name="capability_investment_state",
    )
    op.drop_table("capability_investment_state")
    op.drop_table("capability_market_binding")
    op.drop_table("capability_evidence_binding")
    op.drop_index(
        "ix_personal_capability_state_candidate_id",
        table_name="personal_capability_state",
    )
    op.drop_table("personal_capability_state")
    op.drop_table("candidate_capability_node")
    op.drop_table("capability_relation")
    op.drop_table("capability_node")
    op.drop_table("capability_graph_version")
    op.drop_table("capability_identity")
