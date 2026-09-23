import base64

import pytest

from career_harness.core.plugin import PluginContext, PluginEnvelopeStatus
from career_harness.services.plugin_service import PluginRunner
from career_harness.workers.resume_typst import (
    TypstCompileResult,
    TypstCompilerIdentity,
    TypstWorker,
    typst_registration,
    typst_source,
)


class SandboxFixture:
    identity = TypstCompilerIdentity(version="0.13.1", executable_sha256="a" * 64)

    def __init__(self) -> None:
        self.calls: list[tuple[str, float, int]] = []

    def compile(
        self, source: str, *, timeout_seconds: float, max_output_bytes: int
    ) -> TypstCompileResult:
        self.calls.append((source, timeout_seconds, max_output_bytes))
        return TypstCompileResult(
            pdf_base64=base64.b64encode(b"%PDF-1.7\nfixture").decode(),
            page_count=1,
            text_layer=True,
            reading_order=True,
            layout=True,
        )


def test_typst_source_is_deterministic_and_escapes_commands() -> None:
    content = {"name": "Minnn", "summary": "Verified #platform\\engineer"}
    assert typst_source(content) == typst_source(content)
    assert "\\#platform\\\\engineer" in typst_source(content)


def test_typst_worker_runs_through_permissioned_plugin_envelope() -> None:
    sandbox = SandboxFixture()
    worker = TypstWorker(sandbox)
    registration = typst_registration(worker)
    envelope = PluginRunner().invoke(
        registration,
        request_id="request-typst-fixture",
        capability="resume.render",
        payload={"content": {"name": "Minnn"}},
        context=PluginContext(),
        requested_permissions=("filesystem:temporary-directory",),
    )

    assert envelope.status is PluginEnvelopeStatus.OK
    assert envelope.data["compiler_sha256"] == "a" * 64
    assert envelope.data["page_count"] == 1
    assert sandbox.calls[0][1:] == (10.0, 10_000_000)


def test_typst_worker_denies_undeclared_permissions_and_missing_sandbox() -> None:
    registration = typst_registration(TypstWorker(SandboxFixture()))
    denied = PluginRunner().invoke(
        registration,
        request_id="request-typst-denied",
        capability="resume.render",
        payload={"content": {"name": "Minnn"}},
        context=PluginContext(),
        requested_permissions=("network:internet",),
    )
    assert denied.status is PluginEnvelopeStatus.ERROR
    assert denied.error is not None and denied.error.code == "permission_denied"

    with pytest.raises(RuntimeError, match="sandbox runner not configured"):
        TypstWorker().compile({"name": "Minnn"})
