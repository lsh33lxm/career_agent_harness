from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from career_harness.core.common import FrozenModel, OpaqueId


class JobListingLifecycleStatus(StrEnum):
    ACTIVE = "active"
    PENDING_VERIFICATION = "pending_verification"
    INACTIVE = "inactive"


class JobListingObservation(FrozenModel):
    observation_id: OpaqueId
    source_id: OpaqueId
    query: str = Field(max_length=2048)
    source_ref: str = Field(min_length=1, max_length=4096)
    url_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    first_seen_at: datetime
    last_seen_at: datetime
    last_checked_at: datetime
    consecutive_missing: int = Field(ge=0)
    status: JobListingLifecycleStatus
    last_success_run_id: OpaqueId
