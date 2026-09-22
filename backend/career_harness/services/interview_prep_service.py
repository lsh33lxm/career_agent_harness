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


class InterviewLearningPlanRequest(FrozenModel):
    gaps: tuple[str, ...] = ()


class InterviewSessionEventRequest(FrozenModel):
    session_id: str
    role: InterviewSessionRole
    content: str
    source_refs: tuple[str, ...] = ()


def _score_star_answer(answer: str) -> tuple[int, tuple[str, ...], tuple[str, ...]]:
    """Return a transparent, rule-based STAR signal for a review proposal.

    This is deliberately a heuristic: it evaluates structure only and never
    promotes inferred content into a career fact.
    """
    text = answer.lower()
    signals = {
        "情境": ("情境", "背景", "当时", "场景"),
        "任务": ("任务", "目标", "负责", "需要"),
        "行动": ("行动", "我先", "我负责", "通过", "采用", "实施"),
        "结果": ("结果", "最终", "提升", "降低", "完成", "指标"),
    }
    present = tuple(name for name, terms in signals.items() if any(term in text for term in terms))
    missing = tuple(name for name in signals if name not in present)
    score = len(present)
    if len(answer.strip()) < 40:
        score = max(0, score - 1)
    return score, present, missing


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
        star_score, star_present, star_missing = _score_star_answer(answer_text)
        learning_steps = [f"补充{item}部分的事实与 EvidenceRef" for item in star_missing]
        if not learning_steps:
            learning_steps.append("核对结果中的量化指标，并准备一个可复述的追问答案")
        content = (
            f"问题：{question_text}\n"
            f"用户回答：{answer_text}\n"
            "结构化反馈（规则草稿）：\n"
            "- 回答覆盖度：待用户确认\n"
            "- 证据充分性：需要补充对应的已确认经历或 EvidenceRef\n"
            "- 表达优势：待用户确认\n"
            "- 能力缺口：待用户确认，不自动写入 Capability 或 Fact\n"
            f"STAR 结构评分（规则信号）：{star_score}/4；"
            f"识别到：{('、'.join(star_present) or '无')}\n"
            f"待补充维度：{('、'.join(star_missing) or '无')}\n"
            "学习下一步 proposal：\n"
            + "".join(f"- {step}\n" for step in learning_steps)
            + "- 为每个结论补充可核验来源\n"
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

    def propose_learning_plan(
        self, interview_id: str, *, gaps: tuple[str, ...]
    ) -> KnowledgeProposal:
        interview = self.interviews.get(interview_id)
        if interview is None:
            raise KeyError("interview not found")
        if interview.status is not InterviewStatus.COMPLETED:
            raise ValueError("学习计划需要已完成的面试记录")
        if not interview.evidence_refs:
            raise ValueError("学习计划需要至少一条已保存的面试证据")
        normalized = tuple(dict.fromkeys(item.strip() for item in gaps if item.strip()))
        if len(normalized) > 8:
            raise ValueError("学习计划最多包含 8 个待提升项")
        topics = normalized or ("复盘本次回答中的待确认能力缺口",)
        content = (
            f"来源面试：{interview.entity_id}\n"
            "学习计划状态：待用户审核\n"
            "计划不会自动修改 Capability、Fact 或简历。\n"
            + "\n".join(
                f"{index}. {topic}：补充一个可核验练习，并在完成后附 EvidenceRef。"
                for index, topic in enumerate(topics, start=1)
            )
            + "\n完成条件：用户确认目标、范围和来源后，再创建独立学习任务。"
        )
        return self.knowledge.create_proposal(
            category=KnowledgeCategory.INTERVIEW_STORY,
            title=f"{interview.entity_id} 学习计划草稿",
            content=content,
            authority=KnowledgeAuthority.AI_INFERRED,
            created_by=KnowledgeCreatedBy.RULE,
            evidence_refs=interview.evidence_refs,
        )
