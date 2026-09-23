from __future__ import annotations

from dataclasses import dataclass

from career_harness.core.knowledge.models import (
    KnowledgeAuthority,
    KnowledgeCategory,
    KnowledgeCreatedBy,
    KnowledgeProposal,
)
from career_harness.db.application_repository import ApplicationRepository
from career_harness.db.knowledge_repository import KnowledgeRepository


@dataclass(frozen=True, slots=True)
class OutcomeInsightService:
    applications: ApplicationRepository
    knowledge: KnowledgeRepository

    def propose_offer_preparation(self, application_id: str) -> KnowledgeProposal:
        application = self.applications.get(application_id)
        if application is None:
            raise KeyError("application not found")
        outcomes = self.applications.list_outcomes(application_id)
        offers = tuple(item for item in outcomes if item.result.value == "offer")
        if not offers:
            raise ValueError("Offer 准备需要一条已记录的 Offer 结果")
        latest = offers[0]
        evidence_refs = tuple(dict.fromkeys(latest.evidence_refs))
        content = (
            f"申请：{application_id}\n"
            f"Offer 结果：{latest.entity_id}\n"
            "准备清单（待用户审核）：\n"
            "- 核对职位范围、汇报关系和试用期\n"
            "- 记录薪资、股权、地点与到岗时间的用户确认值\n"
            "- 准备需要向雇主确认的问题\n"
            "所有未提供的字段保持待确认，不会自动推断或写入职业事实。"
        )
        return self.knowledge.create_proposal(
            category=KnowledgeCategory.APPLICATION_HISTORY,
            title=f"{application_id} Offer 准备清单",
            content=content,
            authority=KnowledgeAuthority.RULE_VERIFIED,
            created_by=KnowledgeCreatedBy.RULE,
            evidence_refs=evidence_refs,
        )

    def propose_rejection_pattern(self) -> KnowledgeProposal:
        records: list[tuple[str, str, tuple[str, ...]]] = []
        for application in self.applications.list():
            for outcome in self.applications.list_outcomes(application.entity_id):
                if outcome.result.value == "rejection":
                    records.append(
                        (application.entity_id, outcome.entity_id, outcome.evidence_refs)
                    )
        if not records:
            raise ValueError("至少需要一条已记录的拒信结果")
        evidence_refs = tuple(dict.fromkeys(ref for _, _, refs in records for ref in refs))
        lines = "\n".join(
            f"- 申请 {application_id}：结果 {outcome_id}"
            for application_id, outcome_id, _ in records
        )
        content = (
            f"已记录拒信数量：{len(records)}\n{lines}\n"
            "这是基于结果记录的模式分析提案，不代表拒信原因已知。\n"
            "只有在用户补充并确认原因后，才能形成学习计划或修改职业事实。"
        )
        return self.knowledge.create_proposal(
            category=KnowledgeCategory.APPLICATION_HISTORY,
            title="投递结果模式分析建议",
            content=content,
            authority=KnowledgeAuthority.RULE_VERIFIED,
            created_by=KnowledgeCreatedBy.RULE,
            evidence_refs=evidence_refs,
        )
