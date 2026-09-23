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
from career_harness.core.resume import (
    ResumePatchAction,
    ResumePatchOperation,
    ResumePatchStatus,
    RevisionRef,
)
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
            patch_rows = (
                connection.execute(
                    text(
                        "SELECT p.patch_id, p.revision, p.status, i.base_revision, "
                        "p.review_reason, p.reviewed_at, p.reviewed_by "
                        "FROM resume_patch_revision p "
                        "JOIN resume_patch_identity i ON i.patch_id=p.patch_id "
                        "JOIN resume_target_patch_ref ref ON ref.patch_id=p.patch_id "
                        "WHERE ref.target_profile_id=:target_profile "
                        "AND p.revision=(SELECT MAX(p2.revision) FROM resume_patch_revision p2 "
                        "WHERE p2.patch_id=p.patch_id) "
                        "ORDER BY p.patch_id"
                    ),
                    {
                        "target_profile": "target_profile_"
                        + hashlib.sha256(
                            (staging_row["staging_id"] if staging_row else "").encode()
                        ).hexdigest()[:24]
                    },
                )
                .mappings()
                .all()
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
            "application.resume_revision_attached": "申请关联目标简历版本",
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
            *(row["patch_id"] for row in patch_rows),
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
                "status": "待人工审核",
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
                "status": "已记录" if application.resume_revision_id else "尚未建立关联",
                "entity_id": application.resume_revision_id,
            },
            {
                "key": "resume_patch_reviewed",
                "label": "审核简历修改",
                "status": "待审核"
                if any(row["status"] == "proposed" for row in patch_rows)
                else "已审核",
                "entity_id": patch_rows[0]["patch_id"] if patch_rows else None,
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
        evidence_ref_id = None
        if staging_row:
            evidence_ref_id = (
                "evidence_job_staging_"
                + hashlib.sha256(
                    (staging_row["staging_id"] + staging_row["raw_sha256"]).encode()
                ).hexdigest()[:32]
            )
        base_for_patches = self.resume_studio.repository.resumes.get_base("resume_demo", 1)
        resume_patches = []
        for row in patch_rows:
            patch = self.resume_studio.repository.resumes.get_patch(
                row["patch_id"], row["revision"]
            )
            if patch is None:
                continue
            operations = []
            for operation in patch.operations:
                parts = [
                    part.replace("~1", "/").replace("~0", "~")
                    for part in operation.target_path.split("/")[1:]
                ]
                old_value: object = base_for_patches.sections if base_for_patches else None
                try:
                    for part in parts:
                        old_value = (
                            old_value[int(part)] if isinstance(old_value, list) else old_value[part]
                        )
                except (KeyError, IndexError, TypeError, ValueError):
                    old_value = None
                requirement_index = (
                    0
                    if operation.target_path == "/summary"
                    else int(operation.target_path.rsplit("/", 1)[1]) + 1
                    if operation.target_path.startswith("/skills/")
                    else None
                )
                requirement_id = (
                    "job_requirement_demo_"
                    + hashlib.sha256(
                        (staging_row["staging_id"] + str(requirement_index)).encode()
                    ).hexdigest()[:24]
                    if staging_row and requirement_index is not None
                    else None
                )
                operations.append(
                    {
                        "before": old_value,
                        "after": operation.proposed_value,
                        "target_path": operation.target_path,
                        "reason": operation.reason,
                        "requirement_ids": [requirement_id] if requirement_id else [],
                        "evidence_ids": list(operation.evidence_refs),
                    }
                )
            resume_patches.append(
                {
                    "patch_id": patch.patch_id,
                    "revision": patch.revision,
                    "review_status": patch.status.value,
                    "reviewed_at": patch.reviewed_at.isoformat() if patch.reviewed_at else None,
                    "review_source": "本地演示草稿 / 待人工审核"
                    if patch.status is ResumePatchStatus.PROPOSED
                    else (
                        "用户手动编辑"
                        if any("用户手动编辑" in operation.reason for operation in patch.operations)
                        else "用户审核"
                    ),
                    "review_note": patch.review_reason,
                    "operations": operations,
                }
            )
        links = [
            {"kind": "岗位", "id": opportunity.opportunity.entity_id, "label": "演示岗位"}
            if opportunity is not None
            else None,
            {"kind": "申请", "id": application.entity_id, "label": "演示申请"},
            *[
                {"kind": "JD 要求", "id": row["requirement_id"], "label": row["requirement_text"]}
                for row in requirement_rows
            ],
            *(
                [{"kind": "Evidence", "id": evidence_ref_id, "label": "岗位来源证据"}]
                if evidence_ref_id
                else []
            ),
            *[
                {"kind": "Resume Patch", "id": item["patch_id"], "label": item["review_status"]}
                for item in resume_patches
            ],
            *(
                [
                    {
                        "kind": "ResumeRevision",
                        "id": application.resume_revision_id,
                        "label": "目标简历快照",
                    }
                ]
                if application.resume_revision_id
                else []
            ),
            *[
                {"kind": "面试", "id": item.entity_id, "label": "演示技术面试"}
                for item in interview_rows
            ],
            *[
                {"kind": "知识", "id": row["knowledge_id"], "label": row["title"]}
                for row in knowledge_rows
            ],
        ]
        return {
            "available": True,
            "staging_id": staging_row["staging_id"] if staging_row else None,
            "application_id": application.entity_id,
            "opportunity_id": opportunity.opportunity.entity_id if opportunity else None,
            "resume_revision_id": application.resume_revision_id,
            "application_state": application.state.value,
            "application_revision": application.revision,
            "evidence_ref_id": evidence_ref_id,
            "requirements": [dict(row) for row in requirement_rows],
            "resume_patch": dict(patch_row) if patch_row else None,
            "resume_patches": resume_patches,
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
        patch_ids: list[str] = []
        summary = base.sections.get("summary")
        if isinstance(summary, str) and summary:
            candidates = (
                ("/summary", summary, "等待用户核对岗位相关表述；岗位证据不证明个人经历。"),
                (
                    "/skills/0",
                    "Python",
                    "技能示例待人工核对；关联的是岗位来源证据，不是个人能力证明。",
                ),
                (
                    "/skills/1",
                    "SQLite",
                    "技能示例待人工核对；关联的是岗位来源证据，不是个人能力证明。",
                ),
            )
            for index, (path, value, reason) in enumerate(candidates):
                if path.startswith("/skills/") and (
                    not isinstance(base.sections.get("skills"), list)
                    or len(base.sections["skills"]) <= index - 1
                ):
                    continue
                patch_digest = hashlib.sha256(
                    (record.staging_id + resume_id + str(index)).encode()
                ).hexdigest()[:24]
                patch_id = f"patch_{patch_digest}"
                if self.resume_studio.repository.resumes.get_patch(patch_id) is not None:
                    patch_ids.append(patch_id)
                    continue
                operation = ResumePatchOperation(
                    action=ResumePatchAction.SET,
                    target_path=path,
                    expected_value_hash=canonical_value_hash(
                        base.sections["skills"][index - 1]
                        if path.startswith("/skills/")
                        else summary
                    ),
                    proposed_value=value,
                    evidence_refs=(seed.evidence_ref_id,),
                    requirement_refs=(),
                    reason=reason,
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
                patch_ids.append(patch_id)
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
            patch_id=sorted(patch_ids)[0] if patch_ids else None,
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
        """Compatibility entry point; Demo Mode now stops at preparation/review."""
        self._ensure_demo_resume(resume_id, resume_revision_id, candidate_id)
        result = self.run(
            resume_id=resume_id,
            resume_revision_id=resume_revision_id,
            candidate_id=candidate_id,
            query=query,
            desired_terms=desired_terms,
        )
        return result

    def start_demo(
        self,
        *,
        resume_id: str,
        resume_revision_id: str,
        candidate_id: str,
        query: str = "platform",
        desired_terms: tuple[str, ...] = ("Python", "SQLite"),
    ) -> OfflineCareerLoopResult:
        """Start the durable demo at PREPARING with a reviewable ResumePatch."""
        self._ensure_demo_resume(resume_id, resume_revision_id, candidate_id)
        return self.run(
            resume_id=resume_id,
            resume_revision_id=resume_revision_id,
            candidate_id=candidate_id,
            query=query,
            desired_terms=desired_terms,
        )

    def approve_demo_resume(
        self,
        *,
        patch_id: str,
        application_id: str,
        decision: ResumePatchStatus = ResumePatchStatus.ACCEPTED,
        edited_value: object | None = None,
        review_note: str | None = None,
        resume_id: str = "resume_demo",
        candidate_id: str = "candidate_demo",
    ) -> dict[str, object]:
        """Persist one user decision for an exact Demo ResumePatch."""
        patch = self.resume_studio.repository.resumes.get_patch(patch_id)
        if patch is None:
            raise ValueError("未找到待审核的演示简历修改")
        application = self.applications.repository.get(application_id)
        if application is None:
            raise ValueError("未找到演示申请")
        staging = next(
            (
                item
                for item in self.radar.repository.list()
                if item.admitted_opportunity_id == application.opportunity_id
            ),
            None,
        )
        expected_profile = (
            "target_profile_" + hashlib.sha256(staging.staging_id.encode()).hexdigest()[:24]
            if staging
            else None
        )
        if expected_profile is None or not any(
            ref.patch_id == patch_id
            for ref in self.resume_studio.repository.list_patch_refs(expected_profile)
        ):
            raise ValueError("该 Patch 不属于所选申请的演示岗位")
        if patch.status is not ResumePatchStatus.PROPOSED:
            raise ValueError("该修改已审核；请刷新后查看审核结果")
        if decision not in (ResumePatchStatus.ACCEPTED, ResumePatchStatus.REJECTED):
            raise ValueError("审核状态只能为 accepted 或 rejected")
        edited_operations = None
        if edited_value is not None:
            operation = patch.operations[0].model_copy(
                update={
                    "proposed_value": edited_value,
                    "reason": "用户手动编辑；关联证据仅用于岗位上下文，不构成个人经历证明。",
                }
            )
            edited_operations = (operation, *patch.operations[1:])
        review_reason = review_note or (
            "用户手动编辑并接受" if edited_operations else "用户在本地演示中审核"
        )
        patch = self.resume_studio.resumes.review_patch(
            Command(
                command_id=f"command_demo_review_{patch_id}",
                command_type="resume.patch.demo_review",
                target=EntityRef(entity_id=patch_id, kind=EntityKind.RESUME_PATCH),
                expected_revision=patch.revision,
                idempotency_key=f"demo-review-{patch_id}",
                actor="user",
            ),
            decision=decision,
            review_reason=review_reason,
            edited_operations=edited_operations,
        )
        return {
            "patch_id": patch.patch_id,
            "review_status": patch.status.value,
            "reviewed_at": patch.reviewed_at.isoformat() if patch.reviewed_at else None,
            "review_source": "用户手动编辑" if edited_operations else "用户审核",
            "review_note": patch.review_reason,
            "evidence_ids": list(
                dict.fromkeys(ref for op in patch.operations for ref in op.evidence_refs)
            ),
        }

    def create_demo_resume_revision(
        self, *, application_id: str, resume_id: str = "resume_demo"
    ) -> dict[str, object]:
        application = self.applications.repository.get(application_id)
        if application is None:
            raise ValueError("未找到演示申请")
        staging = next(
            (
                item
                for item in self.radar.repository.list()
                if item.admitted_opportunity_id == application.opportunity_id
            ),
            None,
        )
        if staging is None:
            raise ValueError("演示申请缺少岗位来源")
        profile_id = (
            "target_profile_" + hashlib.sha256(staging.staging_id.encode()).hexdigest()[:24]
        )
        patches = []
        for ref in self.resume_studio.repository.list_patch_refs(profile_id):
            patch = self.resume_studio.repository.resumes.get_patch(ref.patch_id)
            if patch is None:
                raise ValueError("岗位目标简历存在无效 Patch 关联")
            if patch.status is ResumePatchStatus.PROPOSED:
                raise ValueError("仍有待人工审核的简历修改")
            if patch.status is ResumePatchStatus.ACCEPTED:
                patches.append(RevisionRef(entity_id=patch.patch_id, revision=patch.revision))
        if not patches:
            raise ValueError("至少接受一条简历修改后才能生成目标版本")
        patch_key = ":".join(f"{ref.entity_id}@{ref.revision}" for ref in patches)
        revision_id = (
            "resume_revision_demo_target_"
            + hashlib.sha256((application_id + patch_key).encode()).hexdigest()[:24]
        )
        target_revision = self.resume_studio.repository.resumes.get_revision(revision_id)
        if target_revision is None:
            target_revision = self.resume_studio.resumes.create_revision(
                Command(
                    command_id=f"command_{revision_id}",
                    command_type="resume.revision.demo_target",
                    target=EntityRef(entity_id=revision_id, kind=EntityKind.RESUME_REVISION),
                    expected_revision=0,
                    idempotency_key=f"demo-target-revision-{revision_id}",
                    actor="user",
                ),
                resume_id=resume_id,
                base_revision=1,
                accepted_patch_refs=tuple(patches),
            )
        if application.resume_revision_id not in (None, target_revision.revision_id):
            raise ValueError("申请已关联其他简历版本")
        if application.resume_revision_id is None:
            application = self.applications.attach_prepared_resume(
                Command(
                    command_id=f"command_attach_{application_id}_{target_revision.revision_id}",
                    command_type="application.resume_revision_attached",
                    target=EntityRef(entity_id=application_id, kind=EntityKind.APPLICATION),
                    expected_revision=application.revision,
                    idempotency_key=f"demo-attach-{application_id}-{target_revision.revision_id}",
                    actor="user",
                ),
                resume_revision_id=target_revision.revision_id,
            )
        return {
            "resume_revision_id": target_revision.revision_id,
            "application_id": application.entity_id,
            "application_revision": application.revision,
            "application_state": application.state.value,
            "created_at": target_revision.created_at.isoformat(),
            "content_sha256": target_revision.content_sha256,
        }

    def _ensure_demo_resume(
        self, resume_id: str, resume_revision_id: str, candidate_id: str
    ) -> None:
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

    def _continue_demo(
        self, result: OfflineCareerLoopResult, resume_revision_id: str
    ) -> OfflineCareerLoopResult:
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
