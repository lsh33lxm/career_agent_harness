from __future__ import annotations

import hashlib
from dataclasses import dataclass

from career_harness.adapters.job_sources import OfflineFixtureJobSource
from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.knowledge.models import (
    KnowledgeAuthority,
    KnowledgeCategory,
    KnowledgeCreatedBy,
)
from career_harness.core.memory.models import MemoryCreator, MemoryScope, MemoryType
from career_harness.core.resume import ResumePatchAction, ResumePatchOperation
from career_harness.db.knowledge_repository import KnowledgeRepository
from career_harness.db.memory_repository import MemoryRepository
from career_harness.services.application_service import ApplicationService
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
            raise ValueError("离线职位均已处理，无法启动新的闭环")
        admission = self.radar.admit(record.staging_id, actor="user")
        opportunity = admission.admission.opportunity
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
        application_digest = hashlib.sha256(
            (record.staging_id + resume_id).encode()
        ).hexdigest()[:24]
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
            )
            star_prep_proposal_id = star_proposal.proposal_id
        if self.memory is not None:
            memory_proposal = self.memory.create_proposal(
                memory_type=MemoryType.TASK,
                scope_kind=MemoryScope.USER,
                scope_id=candidate_id,
                content=(
                    f"准备岗位 {seed.title}：先审核公司研究与 STAR 面试提案，"
                    "再决定是否进入下一步。"
                ),
                source_type="offline_job_fixture",
                source_locator=f"job-staging://{record.staging_id}",
                source_refs=(seed.evidence_ref_id,),
                confidence=0.5,
                created_by=MemoryCreator.RULE,
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
        )
