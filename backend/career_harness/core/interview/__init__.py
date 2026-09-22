"""User interview session boundary, distinct from market evidence."""

from career_harness.core.common import EntityKind
from career_harness.core.interview.session import InterviewSessionEvent, InterviewSessionRole
from career_harness.core.lifecycle import Interview, InterviewRound, InterviewStatus

ENTITY_KIND = EntityKind.INTERVIEW

__all__ = [
    "ENTITY_KIND",
    "Interview",
    "InterviewRound",
    "InterviewStatus",
    "InterviewSessionEvent",
    "InterviewSessionRole",
]
