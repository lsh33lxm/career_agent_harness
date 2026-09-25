from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, Path
from pydantic import Field

from career_harness.core.common import FrozenModel
from career_harness.services.github_project_service import GitHubAnalysisError, GitHubProjectService
from career_harness.services.source_connector_service import GitHubConnectorService


class GitHubTokenRequest(FrozenModel):
    token: str = Field(min_length=20, max_length=512, repr=False)


class GitHubAnalysisRequest(FrozenModel):
    repository_url: str = Field(min_length=20, max_length=512)
    use_private_token: bool = False
    confirm_read_only_network: bool


@dataclass(frozen=True, slots=True)
class GitHubProjectApi:
    service: GitHubProjectService
    connector_service: GitHubConnectorService | None = None


def _error(error: Exception) -> HTTPException:
    if isinstance(error, LookupError):
        return HTTPException(404, str(error))
    if isinstance(error, GitHubAnalysisError):
        return HTTPException(422, str(error))
    if isinstance(error, ValueError):
        return HTTPException(422, str(error))
    return HTTPException(500, "GitHub 项目分析失败")


def create_github_project_router(api: GitHubProjectApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/github", tags=["github-projects"])

    @router.get("/token-status")
    def token_status() -> dict[str, bool]:
        return api.service.token_status()

    @router.post("/token")
    def save_token(request: GitHubTokenRequest) -> dict[str, bool]:
        try:
            return api.service.save_token(request.token.strip())
        except Exception as error:
            raise _error(error) from error

    @router.post("/analyze")
    def analyze(request: GitHubAnalysisRequest) -> dict[str, object]:
        if not request.confirm_read_only_network:
            raise HTTPException(422, "必须确认只读 GitHub 网络请求")
        try:
            if api.connector_service is not None:
                connector = api.connector_service.get_or_create(
                    display_name=request.repository_url,
                    repository_url=request.repository_url,
                    use_private_token=request.use_private_token,
                    confirm_read_only_network=request.confirm_read_only_network,
                )
                run = api.connector_service.sync(connector.connector_id)
                if run.cursor_after is None:
                    raise RuntimeError("GitHub sync completed without an analysis cursor")
                return api.service.get_analysis(str(run.cursor_after["analysis_id"]))
            return api.service.analyze(request.repository_url, request.use_private_token)
        except Exception as error:
            raise _error(error) from error

    @router.get("/projects/{project_id}/analyses")
    def list_analyses(
        project_id: str = Path(min_length=1, max_length=128),
    ) -> list[dict[str, object]]:
        return api.service.list_for_project(project_id)

    return router
