from pathlib import Path

import pytest

from career_harness.core.interview import InterviewSessionRole
from career_harness.db.interview_session_repository import InterviewSessionRepository
from tests.integration.test_fact_service import _engine


def test_interview_session_events_are_ordered_and_bounded(tmp_path: Path) -> None:
    repository = InterviewSessionRepository(_engine(tmp_path))
    first = repository.append(
        interview_id="interview_session_001",
        session_id="session_001",
        role=InterviewSessionRole.ASSISTANT,
        content="请介绍一个你解决复杂问题的经历。",
    )
    second = repository.append(
        interview_id="interview_session_001",
        session_id="session_001",
        role=InterviewSessionRole.USER,
        content="我在项目中通过证据和回归测试定位了问题。",
    )
    assert (first.sequence, second.sequence) == (1, 2)
    assert [item.role for item in repository.list("session_001")] == [
        InterviewSessionRole.ASSISTANT,
        InterviewSessionRole.USER,
    ]
    with pytest.raises(ValueError, match="不能为空"):
        repository.append(
            interview_id="interview_session_001",
            session_id="session_001",
            role=InterviewSessionRole.USER,
            content="   ",
        )

