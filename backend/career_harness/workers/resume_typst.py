from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import Field

from career_harness.core.common import FrozenModel
from career_harness.core.plugin import PluginContext
from career_harness.core.plugin.contracts import (
    CoreCompatibility,
    PluginCostLimits,
    PluginHealthcheck,
    PluginManifest,
    PluginPermissions,
    PluginReplacement,
    PluginSource,
    PluginType,
)
from career_harness.services.plugin_service import RegisteredPlugin
from career_harness.services.resume_renderer import resume_lines

TYPST_TEMPLATE_ID = "resume-render-typst"
TYPST_TEMPLATE_VERSION = "1.0.0"
TYPST_PLUGIN_ID = "resume-render-typst-worker"
TYPST_PLUGIN_VERSION = "1.0.0"
TYPST_DEFINITION = {
    "compile_command": ["typst", "compile", "resume.typ", "resume.pdf"],
    "fonts": ["system-sans"],
    "page_limit": 3,
    "test_fixture": {"name": "Fixture", "summary": "Local deterministic fixture"},
    "sandbox": "required-external-sandbox-runner",
}


class TypstCompilerIdentity(FrozenModel):
    version: str = Field(min_length=1, max_length=64)
    executable_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class TypstCompileResult(FrozenModel):
    pdf_base64: str = Field(min_length=4)
    page_count: int = Field(ge=1)
    text_layer: bool
    reading_order: bool
    layout: bool

    def pdf_bytes(self) -> bytes:
        output = base64.b64decode(self.pdf_base64, validate=True)
        if not output.startswith(b"%PDF"):
            raise RuntimeError("Typst sandbox did not produce a PDF")
        return output


class TypstSandboxRunner(Protocol):
    @property
    def identity(self) -> TypstCompilerIdentity: ...

    def compile(
        self,
        source: str,
        *,
        timeout_seconds: float,
        max_output_bytes: int,
    ) -> TypstCompileResult: ...


def typst_source(content: dict[str, Any]) -> str:
    escaped = [
        line.replace("\\", "\\\\").replace("#", "\\#")
        for line in resume_lines(content)
    ]
    body = "\n\n".join(escaped)
    return '#set page(paper: "a4")\n#set text(size: 10pt)\n' + body + "\n"


@dataclass(frozen=True, slots=True)
class TypstWorker:
    sandbox: TypstSandboxRunner | None = None

    @property
    def available(self) -> bool:
        return self.sandbox is not None

    @property
    def identity(self) -> TypstCompilerIdentity | None:
        return self.sandbox.identity if self.sandbox is not None else None

    def compile(
        self,
        content: dict[str, Any],
        *,
        timeout_seconds: float = 10,
        max_output_bytes: int = 10_000_000,
    ) -> TypstCompileResult:
        if self.sandbox is None:
            raise RuntimeError("Typst renderer is unavailable: sandbox runner not configured")
        result = self.sandbox.compile(
            typst_source(content),
            timeout_seconds=timeout_seconds,
            max_output_bytes=max_output_bytes,
        )
        if len(result.pdf_bytes()) > max_output_bytes:
            raise RuntimeError("Typst renderer output exceeds declared max_output_bytes")
        return result


def typst_registration(worker: TypstWorker) -> RegisteredPlugin:
    manifest = PluginManifest(
        id=TYPST_PLUGIN_ID,
        name="Resume Renderer / Typst Sandbox",
        version=TYPST_PLUGIN_VERSION,
        api_version="1",
        type=PluginType.WORKER_PLUGIN,
        source=PluginSource(
            repo="builtin://resume-render-typst-worker",
            ref="v1",
            commit="builtin-resume-render-typst-worker-v1",
            license="Apache-2.0",
        ),
        capabilities=("resume.render",),
        permissions=PluginPermissions(filesystem=("temporary-directory",)),
        data_contracts=("ResumeRevision", "PluginEnvelope", "OutputArtifact"),
        healthcheck=PluginHealthcheck(command="health", timeout_ms=1000),
        replacement=PluginReplacement(compatible_capabilities=("resume.render",)),
        dependencies=("typst-sandbox",),
        core_compatibility=CoreCompatibility(min_version="0.1.0", max_version="0.x"),
        data_migration_version=0,
        cost_limits=PluginCostLimits(max_runtime_ms=10_000, max_output_bytes=10_000_000),
        user_visible_description="Typst PDF renderer available only through an injected sandbox.",
        security_url="about:blank",
        terms_url="about:blank",
    )

    def handler(payload: dict[str, Any], context: PluginContext) -> dict[str, Any]:
        context.cancellation.raise_if_cancelled()
        content = payload.get("content")
        if not isinstance(content, dict):
            raise ValueError("Typst renderer requires object content")
        result = worker.compile(
            content,
            timeout_seconds=manifest.cost_limits.max_runtime_ms / 1000,
            max_output_bytes=manifest.cost_limits.max_output_bytes,
        )
        context.cancellation.raise_if_cancelled()
        identity = worker.identity
        if identity is None:
            raise RuntimeError("Typst sandbox identity is unavailable")
        return {
            **result.model_dump(mode="json"),
            "compiler_version": identity.version,
            "compiler_sha256": identity.executable_sha256,
        }

    return RegisteredPlugin(manifest, handler)
