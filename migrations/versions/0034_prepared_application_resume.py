"""Allow prepared applications to pin a resume revision before submission."""

from alembic import op

revision = "0034_prepared_application_resume"
down_revision = "0033_wiki_page_governance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_application_submission_stable")
    with op.batch_alter_table("application_revision_record") as batch:
        batch.drop_constraint("ck_application_submission", type_="check")
        batch.create_check_constraint(
            "ck_application_submission",
            "(state IN ('preparing', 'ready_for_review') AND submission_authority IS NULL "
            "AND submission_evidence_ref_id IS NULL AND submitted_at IS NULL) OR "
            "(state NOT IN ('preparing', 'ready_for_review') AND resume_revision_id IS NOT NULL "
            "AND submission_authority IN ('user_confirmed', 'portal_receipt') "
            "AND submitted_at IS NOT NULL)",
        )
    op.execute(
        "CREATE TRIGGER trg_application_submission_stable BEFORE INSERT "
        "ON application_revision_record WHEN EXISTS (SELECT 1 FROM application_revision_record "
        "AS prior WHERE prior.application_id = NEW.application_id "
        "AND prior.submission_authority IS NOT NULL AND ("
        "prior.resume_revision_id IS NOT NEW.resume_revision_id OR "
        "prior.submission_authority IS NOT NEW.submission_authority OR "
        "prior.submission_evidence_ref_id IS NOT NEW.submission_evidence_ref_id OR "
        "prior.submitted_at IS NOT NEW.submitted_at)) BEGIN "
        "SELECT RAISE(ABORT, 'Application submission identity cannot change'); END"
    )
    for action in ("UPDATE", "DELETE"):
        suffix = "no_update" if action == "UPDATE" else "no_delete"
        op.execute(
            f"CREATE TRIGGER trg_application_revision_record_{suffix} BEFORE {action} "
            "ON application_revision_record BEGIN SELECT RAISE(ABORT, "
            "'application_revision_record is immutable'); END"
        )


def downgrade() -> None:
    with op.batch_alter_table("application_revision_record") as batch:
        batch.drop_constraint("ck_application_submission", type_="check")
        batch.create_check_constraint(
            "ck_application_submission",
            "(state IN ('preparing', 'ready_for_review') AND resume_revision_id IS NULL "
            "AND submission_authority IS NULL AND submission_evidence_ref_id IS NULL "
            "AND submitted_at IS NULL) OR (state NOT IN ('preparing', 'ready_for_review') "
            "AND resume_revision_id IS NOT NULL "
            "AND submission_authority IN ('user_confirmed', 'portal_receipt') "
            "AND submitted_at IS NOT NULL)",
        )
    op.execute("DROP TRIGGER IF EXISTS trg_application_submission_stable")
    for action, suffix in (("UPDATE", "no_update"), ("DELETE", "no_delete")):
        op.execute(
            f"CREATE TRIGGER trg_application_revision_record_{suffix} BEFORE {action} "
            "ON application_revision_record BEGIN SELECT RAISE(ABORT, "
            "'application_revision_record is immutable'); END"
        )
