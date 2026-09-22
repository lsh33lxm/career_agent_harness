from __future__ import annotations

from dataclasses import dataclass

from career_harness.core.common import FrozenModel
from career_harness.core.knowledge.models import (
    KnowledgeAuthority,
    KnowledgeCategory,
    KnowledgeCreatedBy,
    KnowledgeProposal,
)
from career_harness.db.interview_repository import InterviewRepository
from career_harness.db.knowledge_repository import KnowledgeRepository


class InterviewPrepRequest(FrozenModel):
    mode: str = "behavioral"
    focus: str = ""


@dataclass(frozen=True, slots=True)
class InterviewPrepService:
    interviews: InterviewRepository
    knowledge: KnowledgeRepository

    def propose(self, interview_id: str, *, mode: str, focus: str) -> KnowledgeProposal:
        if mode not in {"technical", "behavioral"}:
            raise ValueError("面试准备类型只能是 technical 或 behavioral")
        interview = self.interviews.get(interview_id)
        if interview is None:
            raise KeyError("interview not found")
        if not interview.evidence_refs:
            raise ValueError("面试准备需要至少一条已保存的面试证据")
        focus_text = focus.strip() or "根据岗位要求和已确认经历准备追问"
        content = (
            f"面试类型：{'技术面试' if mode == 'technical' else '行为面试'}\n"
            f"准备重点：{focus_text}\n"
            "仅允许使用已确认经历和引用证据回答；未知内容保持待确认，不自动补全。\n"
            "建议结构：问题 → 事实证据 → 回答草稿 → 待用户确认的缺口。"
        )
        return self.knowledge.create_proposal(
            category=KnowledgeCategory.INTERVIEW_STORY,
            title=f"{interview.entity_id} 面试准备草稿",
            content=content,
            authority=KnowledgeAuthority.AI_INFERRED,
            created_by=KnowledgeCreatedBy.RULE,
            evidence_refs=interview.evidence_refs,
        )
