from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

OpaqueId = Annotated[str, Field(min_length=3, max_length=128, pattern=r"^[a-z][a-z0-9_-]+$")]


def utc_now() -> datetime:
    return datetime.now(UTC)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EntityKind(StrEnum):
    EVIDENCE = "evidence"
    EXTRACTED_CLAIM = "extracted_claim"
    FACT = "fact"
    CANDIDATE = "candidate"
    CAPABILITY_CANDIDATE = "capability_candidate"
    MARKET = "market"
    JOB = "job"
    JOB_REQUIREMENT = "job_requirement"
    MATCH_ASSESSMENT = "match_assessment"
    OPPORTUNITY = "opportunity"
    PROJECT_ENHANCEMENT_TASK = "project_enhancement_task"
    RESUME = "resume"
    RESUME_PATCH = "resume_patch"
    RESUME_REVISION = "resume_revision"
    APPLICATION = "application"
    INTERVIEW = "interview"
    PREP = "prep"
    OUTCOME = "outcome"
    APPROVAL = "approval"
    RUN = "run"
    SNAPSHOT = "snapshot"
    CONTEXT_MANIFEST = "context_manifest"


class EntityRef(FrozenModel):
    entity_id: OpaqueId
    kind: EntityKind
