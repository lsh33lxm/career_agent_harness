from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from career_harness.adapters.job_sources import OfflineFixtureJobSource
from career_harness.core.application import ApplicationState, SubmissionAuthority
from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.interview import InterviewRound
from career_harness.core.knowledge.models import (
    KnowledgeAuthority,
    KnowledgeCategory,
    KnowledgeCreatedBy,
)
from career_harness.core.memory.models import MemoryCreator, MemoryScope, MemoryType
from career_harness.core.resume import ResumePatchAction, ResumePatchOperation
from career_harness.db.knowledge_repository import KnowledgeRepository
from career_harness.db.memory_repository import MemoryRepository
from career_harness.db.opportunity_repository import OpportunityRepository
from career_harness.services.application_service import ApplicationService
from career_harness.services.interview_prep_service import InterviewPrepService
from career_harness.services.interview_service import InterviewService
from career_harness.services.opportunity_radar_service import OpportunityRadarService
from career_harness.services.resume_service import canonical_value_hash
from career_harness.services.resume_studio_service import ResumeStudioService


@dataclass(frozen=True, slots=True)
class OfflineCareerLoopResult:
    staging_id: str
    opportunity_id: str
    opportunity_revision: int
    score: float
    gaps: tuple[str, ...]
    evidence_ref_id: str
    target_profile_id: str
    patch_id: str | None
    resume_revision_id: str
    render_run_id: str
    ats_status: str
    keyword_gaps: tuple[str, ...]
    application_id: str
    application_revision: int
    application_state: str
    company_research_proposal_id: str | None = None
    star_prep_proposal_id: str | None = None
    memory_proposal_id: str | None = None
    application_history_proposal_id: str | None = None
    wiki_proposal_id: str | None = None
    interview_id: str | None = None
    interview_revision: int | None = None
    interview_prep_proposal_id: str | None = None
    interview_feedback_proposal_id: str | None = None


class OfflineCareerLoopService:
    """Run the local, review-gated job-to-resume path with no external writes."""

    def __init__(
        self,
        radar: OpportunityRadarService,
        resume_studio: ResumeStudioService,
        knowledge: KnowledgeRepository | None = None,
        memory: MemoryRepository | None = None,
    ) -> None:
        self.radar = radar
        self.resume_studio = resume_studio
        self.knowledge = knowledge
        self.memory = memory
        self.applications = ApplicationService(resume_studio.commands)
        self.opportunity_repository = OpportunityRepository(radar.engine)

    def run(
        self,
        *,
        resume_id: str,
        resume_revision_id: str,
        candidate_id: str,
        query: str = "platform",
        desired_terms: tuple[str, ...] = ("Python", "SQLite"),
    ) -> OfflineCareerLoopResult:
        staged = self.radar.collect(
            OfflineFixtureJobSource(),
            query=query,
            desired_terms=desired_terms,
        )
        if not staged:
            raise ValueError("离线职位源没有返回可处理的岗位")
        record = next((item for item in staged if item.status.value == "staged"), None)
        if record is None:
            record = next((item for item in staged if item.status.value == "admitted"), None)
        if record is None:
            raise ValueError("离线职位均已处理，无法启动新的闭环")
        if record.status.value == "staged":
            admission = self.radar.admit(record.staging_id, actor="user")
            opportunity = admission.admission.opportunity
        else:
            detail = self.opportunity_repository.get(record.admitted_opportunity_id or "")
            opportunity = detail.opportunity if detail is not None else None
        if opportunity is None:
            raise RuntimeError("岗位 admission 未返回 Opportunity")
        seed = self.radar.resume_proposal_seed(record.staging_id)
        base = self.resume_studio.repository.resumes.get_base(resume_id, 1)
        if base is None or base.candidate_id != candidate_id:
            raise ValueError("闭环需要匹配 candidate 的 ResumeBase#1")
        revision = self.resume_studio.repository.resumes.get_revision(resume_revision_id)
        if revision is None or revision.resume_id != resume_id:
            raise ValueError("闭环需要匹配 ResumeRevision")
        target_profile_digest = hashlib.sha256(record.staging_id.encode()).hexdigest()[:24]
        target_profile_id = f"target_profile_{target_profile_digest}"
        profile = self.resume_studio.create_target_profile(
            target_profile_id=target_profile_id,
            resume_id=resume_id,
            title=seed.title,
            company=seed.company,
            opportunity_id=opportunity.entity_id,
            opportunity_revision=opportunity.revision,
            requirement_refs=(),
            keyword_gaps=seed.keyword_gaps,
            actor="user",
        )
        patch_id: str | None = None
        summary = base.sections.get("summary")
        if isinstance(summary, str) and summary:
            patch_digest = hashlib.sha256((record.staging_id + resume_id).encode()).hexdigest()[:24]
            patch_id = f"patch_{patch_digest}"
            operation = ResumePatchOperation(
                action=ResumePatchAction.SET,
                target_path="/summary",
                expected_value_hash=canonical_value_hash(summary),
                proposed_value=summary,
                evidence_refs=(seed.evidence_ref_id,),
                reason="保留已确认摘要，等待用户补充岗位相关证据；此提案不会自动改写简历事实。",
            )
            command = Command(
                command_id=f"command_{patch_id}",
                command_type="resume.patch.propose",
                target=EntityRef(entity_id=patch_id, kind=EntityKind.RESUME_PATCH),
                expected_revision=0,
                idempotency_key=f"offline-loop-{patch_id}",
                actor="agent:offline-career-loop",
            )
            self.resume_studio.propose_patch(
                command,
                target_profile_id=profile.target_profile_id,
                resume_id=resume_id,
                base_revision=base.revision,
                operations=(operation,),
                generator_run_id=f"run_{record.staging_id}",
            )
        run, report = self.resume_studio.render(
            resume_revision_id=resume_revision_id,
            target_profile_id=profile.target_profile_id,
            template_id=None,
            actor="user",
        )
        application_digest = hashlib.sha256((record.staging_id + resume_id).encode()).hexdigest()[
            :24
        ]
        application_id = f"application_{application_digest}"
        application_command = Command(
            command_id=f"command_{application_id}",
            command_type="application.create",
            target=EntityRef(entity_id=application_id, kind=EntityKind.APPLICATION),
            expected_revision=0,
            idempotency_key=f"offline-loop-{application_id}",
            actor="user",
        )
        application = self.applications.create(
            application_command,
            opportunity_id=opportunity.entity_id,
            opportunity_revision=opportunity.revision,
        )
        company_research_proposal_id = None
        star_prep_proposal_id = None
        memory_proposal_id = None
        application_history_proposal_id = None
        wiki_proposal_id = None
        if self.knowledge is not None:
            company = seed.company or "待确认公司"
            company_proposal = self.knowledge.create_proposal(
                category=KnowledgeCategory.COMPANY,
                title=f"{company} 公司研究草稿",
                content=(
                    f"岗位来源提供的公司名称：{company}\n"
                    "这是离线准备草稿，不代表已验证的公司事实。请用户补充并审核官网、业务与团队信息。"
                ),
                authority=KnowledgeAuthority.AI_INFERRED,
                created_by=KnowledgeCreatedBy.RULE,
                evidence_refs=(seed.evidence_ref_id,),
                proposal_id=f"proposal_offline_company_{record.staging_id[8:24]}",
            )
            company_research_proposal_id = company_proposal.proposal_id
            star_proposal = self.knowledge.create_proposal(
                category=KnowledgeCategory.STAR_STORY,
                title=f"{seed.title} STAR 面试准备草稿",
                content=(
                    f"目标岗位：{seed.title}\n"
                    f"待准备主题：{', '.join(seed.keyword_gaps) or '根据岗位要求补充'}\n"
                    "请从已确认经历中选择 2-4 个故事；本草稿不生成新的个人事实。"
                ),
                authority=KnowledgeAuthority.AI_INFERRED,
                created_by=KnowledgeCreatedBy.RULE,
                evidence_refs=(seed.evidence_ref_id,),
                proposal_id=f"proposal_offline_star_{record.staging_id[8:24]}",
            )
            star_prep_proposal_id = star_proposal.proposal_id
            history_proposal = self.knowledge.create_proposal(
                category=KnowledgeCategory.APPLICATION_HISTORY,
                title=f"{seed.title} 求职结果归档草稿",
                content=(
                    f"申请状态：{application.state.value}\n"
                    "这是本地闭环产生的结果归档草稿；提交、面试和结果均需用户补充证据后审核。"
                ),
                authority=KnowledgeAuthority.AI_INFERRED,
                created_by=KnowledgeCreatedBy.RULE,
                evidence_refs=(seed.evidence_ref_id,),
                proposal_id=f"proposal_offline_history_{record.staging_id[8:24]}",
            )
            application_history_proposal_id = history_proposal.proposal_id
            wiki_proposal = self.knowledge.create_proposal(
                category=KnowledgeCategory.MARKET_SIGNAL,
                title=f"{seed.title} 岗位 Wiki 索引草稿",
                content=(
                    f"岗位：{seed.title}\n公司：{company}\n"
                    "仅整理已有岗位证据，发布前必须由用户审核来源和交叉引用。"
                ),
                authority=KnowledgeAuthority.AI_INFERRED,
                created_by=KnowledgeCreatedBy.RULE,
                evidence_refs=(seed.evidence_ref_id,),
                proposal_id=f"proposal_offline_wiki_{record.staging_id[8:24]}",
            )
            wiki_proposal_id = wiki_proposal.proposal_id
        if self.memory is not None:
            memory_proposal = self.memory.create_proposal(
                memory_type=MemoryType.TASK,
                scope_kind=MemoryScope.USER,
                scope_id=candidate_id,
                content=(
                    f"准备岗位 {seed.title}：先审核公司研究与 STAR 面试提案，再决定是否进入下一步。"
                ),
                source_type="offline_job_fixture",
                source_locator=f"job-staging://{record.staging_id}",
                source_refs=(seed.evidence_ref_id,),
                confidence=0.5,
                created_by=MemoryCreator.RULE,
                proposal_id=f"memory_proposal_offline_{record.staging_id[8:24]}",
            )
            memory_proposal_id = memory_proposal.proposal_id
        return OfflineCareerLoopResult(
            staging_id=record.staging_id,
            opportunity_id=opportunity.entity_id,
            opportunity_revision=opportunity.revision,
            score=record.suggested_score,
            gaps=record.gaps,
            evidence_ref_id=seed.evidence_ref_id,
            target_profile_id=profile.target_profile_id,
            patch_id=patch_id,
            resume_revision_id=resume_revision_id,
            render_run_id=run.render_run_id,
            ats_status=report.status.value,
            keyword_gaps=report.keyword_gaps,
            application_id=application.entity_id,
            application_revision=application.revision,
            application_state=application.state.value,
            company_research_proposal_id=company_research_proposal_id,
            star_prep_proposal_id=star_prep_proposal_id,
            memory_proposal_id=memory_proposal_id,
            application_history_proposal_id=application_history_proposal_id,
            wiki_proposal_id=wiki_proposal_id,
        )

    def run_full_demo(
        self,
        *,
        resume_id: str,
        resume_revision_id: str,
        candidate_id: str,
        query: str = "platform",
        desired_terms: tuple[str, ...] = ("Python", "SQLite"),
    ) -> OfflineCareerLoopResult:
        """Run the complete local Demo Story with durable lifecycle events.

        This deliberately records a user-confirmed *demo* submission; it never
        contacts a portal and never creates a portal receipt.
        """
        if self.resume_studio.repository.resumes.get_base(resume_id, 1) is None:
            self.resume_studio.repository.resumes.save_base_revision(
                Command(
                    command_id=f"command_{resume_id}_seed",
                    command_type="resume.demo_seed",
                    target=EntityRef(entity_id=resume_id, kind=EntityKind.RESUME),
                    expected_revision=0,
                    idempotency_key=f"demo-resume-seed-{resume_id}",
                    actor="user",
                ),
                candidate_id=candidate_id,
                sections={
                    "name": "演示候选人",
                    "contact": "demo@example.invalid",
                    "summary": "已确认的演示经历摘要",
                    "skills": ["Python", "SQLite"],
                },
            )
            self.resume_studio.repository.resumes.create_revision(
                Command(
                    command_id=f"command_{resume_revision_id}_seed",
                    command_type="resume.demo_revision_seed",
                    target=EntityRef(
                        entity_id=resume_revision_id, kind=EntityKind.RESUME_REVISION
                    ),
                    expected_revision=0,
                    idempotency_key=f"demo-resume-revision-seed-{resume_revision_id}",
                    actor="user",
                ),
                resume_id=resume_id,
                base_revision=1,
                accepted_patch_refs=(),
            )
        result = self.run(
            resume_id=resume_id,
            resume_revision_id=resume_revision_id,
            candidate_id=candidate_id,
            query=query,
            desired_terms=desired_terms,
        )
        current = self.applications.repository.get(result.application_id)
        if current is None:
            raise RuntimeError("演示闭环申请记录未持久化")
        if current.state is ApplicationState.PREPARING:
            current = self.applications.set_preparation_state(
                Command(
                    command_id=f"command_demo_ready_{result.application_id}",
                    command_type="application.ready_for_review",
                    target=EntityRef(entity_id=result.application_id, kind=EntityKind.APPLICATION),
                    expected_revision=current.revision,
                    idempotency_key=f"demo-ready-{result.application_id}",
                    actor="user",
                ),
                state=ApplicationState.READY_FOR_REVIEW,
            )
        if current.state is ApplicationState.READY_FOR_REVIEW:
            current = self.applications.record_submission(
                Command(
                    command_id=f"command_demo_submit_{result.application_id}",
                    command_type="application.demo_submission_recorded",
                    target=EntityRef(entity_id=result.application_id, kind=EntityKind.APPLICATION),
                    expected_revision=current.revision,
                    idempotency_key=f"demo-submit-{result.application_id}",
                    actor="user",
                ),
                resume_revision_id=resume_revision_id,
                authority=SubmissionAuthority.USER_CONFIRMED,
            )
        if current.state is ApplicationState.SUBMITTED_BY_USER:
            current = self.applications.advance_state(
                Command(
                    command_id=f"command_demo_interview_{result.application_id}",
                    command_type="application.demo_interview_stage",
                    target=EntityRef(entity_id=result.application_id, kind=EntityKind.APPLICATION),
                    expected_revision=current.revision,
                    idempotency_key=f"demo-interview-stage-{result.application_id}",
                    actor="user",
                ),
                state=ApplicationState.INTERVIEW,
            )

        interview_id = f"interview_demo_{result.application_id.removeprefix('application_')}"
        interview_service = InterviewService(self.resume_studio.commands)
        interview = interview_service.repository.get(interview_id)
        if interview is None:
            interview = interview_service.schedule_interview(
                Command(
                    command_id=f"command_{interview_id}_schedule",
                    command_type="interview.demo_schedule",
                    target=EntityRef(entity_id=interview_id, kind=EntityKind.INTERVIEW),
                    expected_revision=0,
                    idempotency_key=f"demo-schedule-{interview_id}",
                    actor="user",
                ),
                application_id=result.application_id,
                application_revision=current.revision,
                round=InterviewRound.TECHNICAL,
                scheduled_at=datetime(2026, 9, 24, 10, 0, tzinfo=UTC),
                evidence_refs=(result.evidence_ref_id,),
            )
        if interview.revision == 1:
            interview = interview_service.complete_interview(
                Command(
                    command_id=f"command_{interview_id}_complete",
                    command_type="interview.demo_complete",
                    target=EntityRef(entity_id=interview_id, kind=EntityKind.INTERVIEW),
                    expected_revision=1,
                    idempotency_key=f"demo-complete-{interview_id}",
                    actor="user",
                ),
                evidence_refs=(result.evidence_ref_id,),
            )

        prep = (
            InterviewPrepService(interview_service.repository, self.knowledge)
            if self.knowledge
            else None
        )
        prep_proposal_id = None
        feedback_proposal_id = None
        if prep is not None:
            prep_proposal = prep.propose(
                interview_id,
                mode="technical",
                focus="岗位要求与项目证据",
                proposal_id=f"proposal_demo_interview_prep_{interview_id.removeprefix('interview_')}",
            )
            feedback = prep.propose_feedback(
                interview_id,
                question="请说明你如何验证一个本地优先的职业工作台。",
                answer=(
                    "情境：需要在本地保存证据。任务：保证岗位、简历和申请可追溯。"
                    "行动：我采用 SQLite、不可变证据和人工审核。结果：形成可回放的演示闭环。"
                ),
                proposal_id=f"proposal_demo_interview_feedback_{interview_id.removeprefix('interview_')}",
            )
            prep_proposal_id = prep_proposal.proposal_id
            feedback_proposal_id = feedback.proposal_id
        return replace(
            result,
            application_revision=current.revision,
            application_state=current.state.value,
            interview_id=interview.entity_id,
            interview_revision=interview.revision,
            interview_prep_proposal_id=prep_proposal_id,
            interview_feedback_proposal_id=feedback_proposal_id,
        )
