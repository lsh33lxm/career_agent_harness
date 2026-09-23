"""Candidate-scoped Capability Workspace derived read model."""

from career_harness.core.capability_workspace.models import (
    CAPABILITY_WORKSPACE_VERSION,
    CapabilityProjection,
    CapabilityWorkspace,
    WorkspaceInputKind,
    WorkspaceInputRef,
    build_capability_workspace,
)

__all__ = [
    "CAPABILITY_WORKSPACE_VERSION",
    "CapabilityProjection",
    "CapabilityWorkspace",
    "WorkspaceInputKind",
    "WorkspaceInputRef",
    "build_capability_workspace",
]
