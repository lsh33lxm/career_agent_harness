from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from sqlalchemy import text

from career_harness.adapters.job_sources import OfflineFixtureJobSource
from career_harness.core.application import ApplicationState, SubmissionAuthority
from career_harness.core.capability import CapabilityEvidenceScope
from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.interview import InterviewRound
from career_harness.core.job import JobRef, JobRequirementImportance
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
from career_harness.services.resume_service import ResumeService, canonical_value_hash
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
    requirement_ids: tuple[str, ...] = ()
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

    def demo_story(self) -> dict[str, object]:
        """Return the durable Demo Story read model without creating data."""
        applications = tuple(
            item
            for item in self.applications.repository.list()
            if item.entity_id.startswith("application_")
        )
        if not applications:
            return {
                "available": False,
                "message": "尚未运行演示闭环",
                "steps": [],
                "events": [],
                "links": [],
            }
        application = applications[0]
        opportunity = self.opportunity_repository.get(application.opportunity_id)
        interviews = self.applications.repository.engine
        interview_rows = tuple(
            InterviewService(self.resume_studio.commands).repository.list_for_application(
                application.entity_id
            )
        )
        with interviews.connect() as connection:
            staging_row = (
                connection.execute(
                    text(
                        "SELECT staging_id, raw_sha256, suggested_score, gaps, admitted_job_id "
                        "FROM job_staging_record WHERE admitted_opportunity_id=:opportunity "
                        "ORDER BY created_at LIMIT 1"
                    ),
                    {"opportunity": application.opportunity_id},
                )
                .mappings()
                .first()
            )
            requirement_rows = (
                connection.execute(
                    text(
                        "SELECT requirement_id, requirement_text, status "
                        "FROM job_requirement_revision WHERE job_id=:job_id "
                        "AND job_revision=:revision ORDER BY requirement_id"
                    ),
                    {
                        "job_id": staging_row["admitted_job_id"] if staging_row else "",
                        "revision": 1,
                    },
                )
                .mappings()
                .all()
            )
            patch_row = (
                connection.execute(
                    text(
                        "SELECT p.patch_id, p.revision, p.status, "
                        "i.base_revision, p.review_reason "
                        "FROM resume_patch_revision p "
                        "JOIN resume_patch_identity i ON i.patch_id=p.patch_id "
                        "JOIN resume_target_patch_ref ref ON ref.patch_id=p.patch_id "
                        "WHERE ref.target_profile_id=:target_profile "
                        "ORDER BY p.patch_id, p.revision DESC LIMIT 1"
                    ),
                    {
                        "target_profile": "target_profile_"
                        + hashlib.sha256(
                            (staging_row["staging_id"] if staging_row else "").encode()
                        ).hexdigest()[:24]
                    },
                )
                .mappings()
                .first()
            )
            rows = (
                connection.execute(
                    text(
                        "SELECT event_id, event_type, entity_id, entity_revision, occurred_at "
                        "FROM domain_event ORDER BY occurred_at, event_id"
                    )
                )
                .mappings()
                .all()
            )
            knowledge_rows = (
                connection.execute(
                    text(
                        "SELECT proposal_id AS knowledge_id, 1 AS current_revision, "
                        "title, status "
                        "FROM knowledge_proposal "
                        "WHERE status='pending' AND category IN "
                        "('company', 'star_story', 'application_history', 'market_signal') "
                        "ORDER BY proposal_id LIMIT 20"
                    ),
                )
                .mappings()
                .all()
            )
        labels = {
            "opportunity.admitted": "岗位被发现",
            "application.create": "创建申请",
            "application.ready_for_review": "进入人工审核",
            "application.demo_submission_recorded": "记录用户已投递（演示）",
            "application.demo_interview_stage": "进入面试阶段",
            "interview.demo_schedule": "创建面试准备",
            "interview.demo_complete": "完成面试复盘",
        }
        relevant_ids = {
            application.entity_id,
            application.opportunity_id,
            application.resume_revision_id,
            *(item.entity_id for item in interview_rows),
        }
        events = [
            {
                "event_id": row["event_id"],
                "event_type": row["event_type"],
                "label": labels.get(row["event_type"], "已记录操作"),
                "entity_id": row["entity_id"],
                "revision": row["entity_revision"],
                "occurred_at": row["occurred_at"],
            }
            for row in rows
            if row["entity_id"] in relevant_ids or "demo" in row["event_type"]
        ]
        steps = [
            {
                "key": "job_found",
                "label": "岗位被发现",
                "status": "已记录",
                "entity_id": opportunity.opportunity.entity_id if opportunity else None,
            },
            {
                "key": "jd_reviewed",
                "label": "确认 JD 要求",
                "status": "已记录",
                "entity_id": opportunity.opportunity.entity_id if opportunity else None,
            },
            {
                "key": "evidence_matched",
                "label": "匹配证据与能力差距",
                "status": "已记录",
                "entity_id": application.opportunity_id,
            },
            {
                "key": "resume_created",
                "label": "创建目标简历",
                "status": "已记录",
                "entity_id": application.resume_revision_id,
            },
            {
                "key": "application_created",
                "label": "创建申请",
                "status": "已记录",
                "entity_id": application.entity_id,
            },
            {
                "key": "application_progressed",
                "label": "更新申请状态",
                "status": application.state.value,
                "entity_id": application.entity_id,
            },
            {
                "key": "interview_prepared",
                "label": "创建面试准备",
                "status": "已记录" if interview_rows else "尚未建立关联",
                "entity_id": interview_rows[0].entity_id if interview_rows else None,
            },
            {
                "key": "interview_reviewed",
                "label": "完成面试复盘",
                "status": "已记录"
                if interview_rows and interview_rows[0].status.value == "completed"
                else "尚未建立关联",
                "entity_id": interview_rows[0].entity_id if interview_rows else None,
            },
        ]
        links = [
            {"kind": "岗位", "id": opportunity.opportunity.entity_id, "label": "演示岗位"}
            if opportunity is not None
            else None,
            {"kind": "申请", "id": application.entity_id, "label": "演示申请"},
            *[
                {"kind": "面试", "id": item.entity_id, "label": "演示技术面试"}
                for item in interview_rows
            ],
            *[
                {"kind": "知识", "id": row["knowledge_id"], "label": row["title"]}
                for row in knowledge_rows
            ],
        ]
        evidence_ref_id = None
        if staging_row:
            evidence_ref_id = (
                "evidence_job_staging_"
                + hashlib.sha256(
                    (staging_row["staging_id"] + staging_row["raw_sha256"]).encode()
                ).hexdigest()[:32]
            )
        return {
            "available": True,
            "staging_id": staging_row["staging_id"] if staging_row else None,
            "application_id": application.entity_id,
            "opportunity_id": opportunity.opportunity.entity_id if opportunity else None,
            "resume_revision_id": application.resume_revision_id,
            "evidence_ref_id": evidence_ref_id,
            "requirements": [dict(row) for row in requirement_rows],
            "resume_patch": dict(patch_row) if patch_row else None,
            "score": staging_row["suggested_score"] if staging_row else None,
            "gaps": (
                json.loads(staging_row["gaps"])
                if staging_row and isinstance(staging_row["gaps"], str)
                else staging_row["gaps"]
                if staging_row
                else []
            ),
            "interviews": [item.model_dump(mode="json") for item in interview_rows],
            "steps": steps,
            "events": events,
            "links": [item for item in links if item is not None],
        }

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
            record = self.radar.repository.get(record.staging_id) or record
        else:
            detail = self.opportunity_repository.get(record.admitted_opportunity_id or "")
            opportunity = detail.opportunity if detail is not None else None
        if opportunity is None:
            raise RuntimeError("岗位 admission 未返回 Opportunity")
        seed = self.radar.resume_proposal_seed(record.staging_id)
        requirement_ids: list[str] = []
        if record.admitted_job_id:
            job_revision = JobRef(job_id=record.admitted_job_id, revision=1)
            for ordinal, requirement_text in enumerate(seed.requirement_texts):
                digest = hashlib.sha256((record.staging_id + str(ordinal)).encode()).hexdigest()[
                    :24
                ]
                requirement_id = f"job_requirement_demo_{digest}"
                self.radar.jobs.propose_requirement(
                    Command(
                        command_id=f"command_{requirement_id}",
                        command_type="job_requirement.demo_propose",
                        target=EntityRef(entity_id=requirement_id, kind=EntityKind.JOB_REQUIREMENT),
                        expected_revision=0,
                        idempotency_key=f"demo-job-requirement-{requirement_id}",
                        actor="agent:offline-career-loop",
                    ),
                    job=job_revision,
                    requirement_text=requirement_text,
                    importance=JobRequirementImportance.REQUIRED,
                    required_scopes=(CapabilityEvidenceScope.EVIDENCE,),
                    source_evidence_refs=(seed.evidence_ref_id,),
                )
                requirement_ids.append(requirement_id)
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
            requirement_ids=tuple(requirement_ids),
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
            resume_service = ResumeService(self.resume_studio.commands)
            resume_service.save_base_revision(
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
            resume_service.create_revision(
                Command(
                    command_id=f"command_{resume_revision_id}_seed",
                    command_type="resume.demo_revision_seed",
                    target=EntityRef(entity_id=resume_revision_id, kind=EntityKind.RESUME_REVISION),
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
