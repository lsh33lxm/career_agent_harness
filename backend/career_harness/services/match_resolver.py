from __future__ import annotations

from collections.abc import Iterable

from career_harness.core.capability import (
    CapabilityNode,
    EvidenceBinding,
    PersonalCapabilityState,
)
from career_harness.core.common import OpaqueId
from career_harness.core.evidence import EvidenceRef
from career_harness.core.job import JobRef, JobRequirement, JobRevision
from career_harness.core.match_gap import (
    MatchInputManifest,
    MatchPolicyInput,
    PersonalCapabilityInputRef,
    ProjectCapabilityInputRef,
)
from career_harness.core.opportunity import OpportunityDetail
from career_harness.core.project import ProjectCapabilityState, ProjectEvidence
from career_harness.db.capability_repository import CapabilityRepository
from career_harness.db.evidence_repository import EvidenceRepository
from career_harness.db.job_repository import JobRepository
from career_harness.db.opportunity_repository import OpportunityRepository
from career_harness.db.project_repository import ProjectRepository


class MatchResolutionError(ValueError):
    """A frozen Match input reference is missing, dangling or identity-drifting."""


class MatchInputResolver:
    """Builds MatchPolicyInput from exact reads only; never latest-at-read.

    Requirements arrive as caller-supplied ordered ``(requirement_id, revision)`` refs;
    project capability states arrive as caller-supplied exact
    ``(capability_state_id, revision)`` refs. Replay resolves the same entities from a
    stored ``MatchInputManifest`` through :meth:`resolve_manifest`. Any missing, stale or
    identity-drifting reference raises :class:`MatchResolutionError`; the resolver never
    skips, substitutes or downgrades provenance.
    """

    def __init__(
        self,
        *,
        opportunities: OpportunityRepository,
        jobs: JobRepository,
        capabilities: CapabilityRepository,
        evidence: EvidenceRepository,
        projects: ProjectRepository,
    ) -> None:
        self.opportunities = opportunities
        self.jobs = jobs
        self.capabilities = capabilities
        self.evidence = evidence
        self.projects = projects

    def resolve(
        self,
        *,
        opportunity_id: OpaqueId,
        opportunity_revision: int,
        candidate_id: OpaqueId,
        requirements: tuple[tuple[OpaqueId, int], ...],
        project_capability_states: tuple[tuple[OpaqueId, int], ...] = (),
    ) -> MatchPolicyInput:
        """Resolve a fresh Match input from caller-supplied exact refs.

        Requirement order follows the caller; personal capability states resolve to the
        current exact revision per ``(candidate_id, capability_id)`` and fail closed on
        ambiguous identities.
        """
        if not requirements:
            raise MatchResolutionError("a Match input requires at least one requirement ref")
        opportunity = self._opportunity(opportunity_id, opportunity_revision)
        job = self._job(opportunity.job)
        requirement_models = tuple(
            self._requirement(requirement_id, revision) for requirement_id, revision in requirements
        )
        official = self._official_nodes(
            (item.capability_id, item.graph_version_id) for item in requirement_models
        )
        states = tuple(
            state
            for capability_id in _ordered_unique(
                item.capability_id for item in requirement_models if item.capability_id is not None
            )
            if (state := self._current_personal_state(candidate_id, capability_id)) is not None
        )
        bindings = tuple(binding for state in states for binding in self._bindings_for(state))
        evidence_refs, project_evidence = self._binding_sources(bindings)
        project_states = tuple(
            self._project_state(state_id, revision)
            for state_id, revision in project_capability_states
        )
        return MatchPolicyInput(
            opportunity=opportunity,
            job=job,
            requirements=requirement_models,
            official_capabilities=official,
            candidate_id=candidate_id,
            personal_states=states,
            evidence_bindings=bindings,
            evidence_refs=evidence_refs,
            project_evidence=project_evidence,
            project_capability_states=project_states,
        )

    def resolve_manifest(
        self, manifest: MatchInputManifest, *, candidate_id: OpaqueId
    ) -> MatchPolicyInput:
        """Re-resolve a stored replay manifest; every input comes from the manifest."""
        opportunity = self._opportunity(
            manifest.opportunity.entity_id, manifest.opportunity.revision
        )
        job = self._job(JobRef(job_id=manifest.job.entity_id, revision=manifest.job.revision))
        requirement_models = tuple(
            self._requirement(item.requirement_id, item.revision) for item in manifest.requirements
        )
        official = self._official_nodes(
            (item.capability_id, item.graph_version_id) for item in manifest.official_capabilities
        )
        states = tuple(
            self._exact_personal_state(item, candidate_id=candidate_id)
            for item in manifest.personal_states
        )
        bindings = tuple(
            binding
            for item in manifest.personal_states
            for binding in self.capabilities.list_evidence_bindings(
                personal_state_id=item.personal_state_id,
                personal_state_revision=item.revision,
            )
        )
        self._verify_bindings_against_manifest(bindings, manifest)
        evidence_refs, project_evidence = self._binding_sources(bindings)
        project_states = tuple(
            self._exact_project_state(item) for item in manifest.project_capability_states
        )
        return MatchPolicyInput(
            opportunity=opportunity,
            job=job,
            requirements=requirement_models,
            official_capabilities=official,
            candidate_id=candidate_id,
            personal_states=states,
            evidence_bindings=bindings,
            evidence_refs=evidence_refs,
            project_evidence=project_evidence,
            project_capability_states=project_states,
        )

    def _opportunity(self, opportunity_id: str, revision: int) -> OpportunityDetail:
        detail = self.opportunities.get_revision(opportunity_id, revision)
        if detail is None:
            raise MatchResolutionError(
                f"exact Opportunity revision is missing: {opportunity_id}@{revision}"
            )
        return detail

    def _job(self, ref: JobRef) -> JobRevision:
        job = self.jobs.get_job(ref.job_id, ref.revision)
        if job is None:
            raise MatchResolutionError(
                f"exact Job revision is missing: {ref.job_id}@{ref.revision}"
            )
        return job

    def _requirement(self, requirement_id: str, revision: int) -> JobRequirement:
        requirement = self.jobs.get_requirement(requirement_id, revision)
        if requirement is None:
            raise MatchResolutionError(
                f"exact JobRequirement revision is missing: {requirement_id}@{revision}"
            )
        return requirement

    def _official_nodes(
        self, refs: Iterable[tuple[OpaqueId | None, OpaqueId | None]]
    ) -> tuple[CapabilityNode, ...]:
        # Graph versions are immutable once released (D-007), so listing the nodes of an
        # exact graph version is an exact read, never latest-at-read.
        wanted = {ref for ref in refs if ref[0] is not None and ref[1] is not None}
        nodes: dict[tuple[str, str], CapabilityNode] = {}
        for graph_version_id in sorted({item[1] for item in wanted}):
            for node in self.capabilities.list_nodes(graph_version_id):
                key = (node.capability_id, node.graph_version_id)
                if key in wanted:
                    nodes[key] = node
        missing = wanted - set(nodes)
        if missing:
            raise MatchResolutionError(
                f"exact official capability node is missing: {sorted(missing)}"
            )
        return tuple(nodes[key] for key in sorted(nodes))

    def _current_personal_state(
        self, candidate_id: str, capability_id: str
    ) -> PersonalCapabilityState | None:
        history = self.capabilities.list_personal_states(
            candidate_id=candidate_id, capability_id=capability_id
        )
        identities = {state.personal_state_id for state in history}
        if not identities:
            return None
        if len(identities) != 1:
            raise MatchResolutionError(
                "ambiguous personal capability identity for "
                f"({candidate_id}, {capability_id}): {sorted(identities)}"
            )
        personal_state_id = identities.pop()
        revision = max(state.revision for state in history)
        state = self.capabilities.get_personal_state(
            personal_state_id=personal_state_id, revision=revision
        )
        if state is None:
            raise MatchResolutionError(
                f"exact Personal Capability State is missing: {personal_state_id}@{revision}"
            )
        self._check_personal_state_identity(
            state, candidate_id=candidate_id, capability_id=capability_id
        )
        return state

    def _exact_personal_state(
        self, ref: PersonalCapabilityInputRef, *, candidate_id: str
    ) -> PersonalCapabilityState:
        if ref.candidate_id != candidate_id:
            raise MatchResolutionError(
                f"manifest personal state {ref.personal_state_id} belongs to another candidate"
            )
        state = self.capabilities.get_personal_state(
            personal_state_id=ref.personal_state_id, revision=ref.revision
        )
        if state is None:
            raise MatchResolutionError(
                "exact Personal Capability State is missing: "
                f"{ref.personal_state_id}@{ref.revision}"
            )
        self._check_personal_state_identity(
            state, candidate_id=ref.candidate_id, capability_id=ref.capability_id
        )
        return state

    @staticmethod
    def _check_personal_state_identity(
        state: PersonalCapabilityState, *, candidate_id: str, capability_id: str
    ) -> None:
        if state.candidate_id != candidate_id or state.capability_id != capability_id:
            raise MatchResolutionError(
                f"Personal Capability State identity drifted: {state.personal_state_id}"
            )

    def _bindings_for(self, state: PersonalCapabilityState) -> tuple[EvidenceBinding, ...]:
        return self.capabilities.list_evidence_bindings(
            personal_state_id=state.personal_state_id,
            personal_state_revision=state.revision,
        )

    @staticmethod
    def _verify_bindings_against_manifest(
        bindings: tuple[EvidenceBinding, ...], manifest: MatchInputManifest
    ) -> None:
        loaded = {binding.binding_id: binding for binding in bindings}
        expected = {item.binding_id: item for item in manifest.evidence_bindings}
        if set(loaded) != set(expected):
            raise MatchResolutionError(
                "Evidence Bindings drifted from the stored manifest: "
                f"missing {sorted(set(expected) - set(loaded))}, "
                f"unexpected {sorted(set(loaded) - set(expected))}"
            )
        for binding_id, ref in expected.items():
            binding = loaded[binding_id]
            if (
                binding.personal_state_id,
                binding.personal_state_revision,
                binding.capability_id,
                binding.evidence_ref_id,
                binding.project_evidence_id,
                binding.project_evidence_revision,
                binding.authority,
                frozenset(binding.scopes),
            ) != (
                ref.personal_state_id,
                ref.personal_state_revision,
                ref.capability_id,
                ref.evidence_ref_id,
                ref.project_evidence_id,
                ref.project_evidence_revision,
                ref.authority,
                frozenset(ref.scopes),
            ):
                raise MatchResolutionError(
                    f"Evidence Binding fields drifted from the stored manifest: {binding_id}"
                )

    def _binding_sources(
        self, bindings: tuple[EvidenceBinding, ...]
    ) -> tuple[tuple[EvidenceRef, ...], tuple[ProjectEvidence, ...]]:
        evidence_refs: dict[str, EvidenceRef] = {}
        project_evidence: dict[tuple[str, int], ProjectEvidence] = {}
        for binding in bindings:
            if binding.evidence_ref_id is not None:
                # capability_evidence_binding.evidence_ref_id predates migration 0007 and
                # has no DB FK; every generic EvidenceRef is resolved one by one.
                if binding.evidence_ref_id in evidence_refs:
                    continue
                provenance = self.evidence.get(binding.evidence_ref_id)
                if provenance is None:
                    raise MatchResolutionError(
                        f"Evidence Binding {binding.binding_id} has a dangling "
                        f"EvidenceRef: {binding.evidence_ref_id}"
                    )
                evidence_refs[binding.evidence_ref_id] = provenance.evidence_ref
            else:
                key = (binding.project_evidence_id, binding.project_evidence_revision)
                if key in project_evidence:
                    continue
                source = self.projects.get_evidence(key[0], key[1])
                if source is None:
                    raise MatchResolutionError(
                        f"Evidence Binding {binding.binding_id} has a dangling "
                        f"Project Evidence ref: {key[0]}@{key[1]}"
                    )
                project_evidence[key] = source
        return (
            tuple(evidence_refs[key] for key in sorted(evidence_refs)),
            tuple(project_evidence[key] for key in sorted(project_evidence)),
        )

    def _project_state(self, capability_state_id: str, revision: int) -> ProjectCapabilityState:
        state = self.projects.get_project_capability_state(capability_state_id, revision)
        if state is None:
            raise MatchResolutionError(
                f"exact Project Capability State is missing: {capability_state_id}@{revision}"
            )
        return state

    def _exact_project_state(self, ref: ProjectCapabilityInputRef) -> ProjectCapabilityState:
        state = self._project_state(ref.capability_state_id, ref.revision)
        if state.project_id != ref.project_id or state.capability_id != ref.capability_id:
            raise MatchResolutionError(
                f"Project Capability State identity drifted: {ref.capability_state_id}"
            )
        return state


def _ordered_unique(items: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))
