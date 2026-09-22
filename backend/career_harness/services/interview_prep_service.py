from __future__ import annotations

from dataclasses import dataclass

from career_harness.core.common import FrozenModel
from career_harness.core.interview import (
    InterviewSessionEvent,
    InterviewSessionRole,
    InterviewStatus,
)
from career_harness.core.knowledge.models import (
    KnowledgeAuthority,
    KnowledgeCategory,
    KnowledgeCreatedBy,
    KnowledgeProposal,
)
from career_harness.db.interview_repository import InterviewRepository
from career_harness.db.interview_session_repository import InterviewSessionRepository
from career_harness.db.knowledge_repository import KnowledgeRepository


class InterviewPrepRequest(FrozenModel):
    mode: str = "behavioral"
    focus: str = ""


class InterviewFeedbackRequest(FrozenModel):
    answer: str
    question: str = ""


class InterviewSessionEventRequest(FrozenModel):
    session_id: str
    role: InterviewSessionRole
    content: str
    source_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class InterviewPrepService:
    interviews: InterviewRepository
    knowledge: KnowledgeRepository
    sessions: InterviewSessionRepository | None = None

    def append_session_event(
        self, interview_id: str, request: InterviewSessionEventRequest
    ) -> InterviewSessionEvent:
        interview = self.interviews.get(interview_id)
        if interview is None:
            raise KeyError("interview not found")
        if self.sessions is None:
            raise RuntimeError("面试会话存储未配置")
        if any(ref not in interview.evidence_refs for ref in request.source_refs):
            raise ValueError("面试会话引用必须来自该面试的 exact EvidenceRef")
        return self.sessions.append(
            interview_id=interview_id,
            session_id=request.session_id,
            role=request.role,
            content=request.content,
            source_refs=request.source_refs,
        )

    def list_session_events(
        self, interview_id: str, session_id: str
    ) -> tuple[InterviewSessionEvent, ...]:
        interview = self.interviews.get(interview_id)
        if interview is None:
            raise KeyError("interview not found")
        if self.sessions is None:
            raise RuntimeError("面试会话存储未配置")
        events = self.sessions.list(session_id)
        if any(item.interview_id != interview_id for item in events):
            raise ValueError("会话与面试记录不匹配")
        return events

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

    def propose_feedback(
        self, interview_id: str, *, question: str, answer: str
    ) -> KnowledgeProposal:
        interview = self.interviews.get(interview_id)
        if interview is None:
            raise KeyError("interview not found")
        if interview.status is not InterviewStatus.COMPLETED:
            raise ValueError("面试复盘需要已完成的面试记录")
        if not interview.evidence_refs:
            raise ValueError("面试复盘需要至少一条已保存的面试证据")
        answer_text = answer.strip()
        if not answer_text:
            raise ValueError("面试回答不能为空")
        if len(answer_text) > 20_000:
            raise ValueError("面试回答超过 20000 字限制")
        question_text = question.strip() or "未记录题目（待用户补充）"
        content = (
            f"问题：{question_text}\n"
            f"用户回答：{answer_text}\n"
            "结构化反馈（规则草稿）：\n"
            "- 回答覆盖度：待用户确认\n"
            "- 证据充分性：需要补充对应的已确认经历或 EvidenceRef\n"
            "- 表达优势：待用户确认\n"
            "- 能力缺口：待用户确认，不自动写入 Capability 或 Fact\n"
            "学习下一步 proposal：\n"
            "- 用 STAR 结构重写一次回答\n"
            "- 为每个结论补充可核验来源\n"
            "- 用户确认后再生成学习任务\n"
            "STAR 复盘草稿：\n"
            "- 情境：待用户确认\n"
            "- 任务：待用户确认\n"
            "- 行动：从回答中提取后由用户确认\n"
            "- 结果：待用户确认\n"
            "- 追问与改进：待用户补充\n"
            "以上内容是复盘提案，不会自动写入职业事实。"
        )
        return self.knowledge.create_proposal(
            category=KnowledgeCategory.INTERVIEW_STORY,
            title=f"{interview.entity_id} 面试复盘草稿",
            content=content,
            authority=KnowledgeAuthority.AI_INFERRED,
            created_by=KnowledgeCreatedBy.RULE,
            evidence_refs=interview.evidence_refs,
        )
