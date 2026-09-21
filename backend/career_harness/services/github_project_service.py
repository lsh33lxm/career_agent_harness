from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

from sqlalchemy import Engine, text

from career_harness.platform.secure_store import WritableSecretStore

MAX_FILES = 5_000
MAX_BYTES = 100 * 1024 * 1024
MAX_TEXT_BYTES = 2 * 1024 * 1024


class GitHubAnalysisError(ValueError):
    pass


def normalize_github_url(value: str) -> tuple[str, str, str]:
    parsed = urlparse(value.strip())
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise GitHubAnalysisError("仅支持标准 https://github.com/owner/repository 地址")
    parts = [item for item in parsed.path.strip("/").split("/") if item]
    if len(parts) != 2:
        raise GitHubAnalysisError("GitHub 地址必须只包含 owner 和 repository")
    owner, repository = parts
    if repository.endswith(".git"):
        repository = repository[:-4]
    if not owner or not repository or any(part in {".", ".."} for part in (owner, repository)):
        raise GitHubAnalysisError("GitHub owner 或 repository 无效")
    return f"https://github.com/{owner}/{repository}", owner, repository


@dataclass(frozen=True, slots=True)
class FetchedRepository:
    root: Path
    commit_sha: str
    file_count: int
    byte_count: int


class RepositoryFetcher(Protocol):
    def fetch(self, url: str, cache_root: Path, token: str | None) -> FetchedRepository: ...


class GitCliRepositoryFetcher:
    def fetch(self, url: str, cache_root: Path, token: str | None) -> FetchedRepository:
        cache_root.mkdir(parents=True, exist_ok=True)
        cache_key = hashlib.sha256(url.encode()).hexdigest()
        target = (cache_root / cache_key).resolve()
        if target.parent != cache_root.resolve():
            raise GitHubAnalysisError("缓存路径越界")
        if target.exists():
            shutil.rmtree(target)
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_CONFIG_COUNT": "2" if token else "1",
                "GIT_CONFIG_KEY_0": "core.hooksPath",
                "GIT_CONFIG_VALUE_0": "NUL" if os.name == "nt" else "/dev/null",
            }
        )
        if token:
            environment.update(
                {
                    "GIT_CONFIG_KEY_1": "http.extraHeader",
                    "GIT_CONFIG_VALUE_1": f"Authorization: Bearer {token}",
                }
            )
        command = [
            "git",
            "clone",
            "--depth",
            "50",
            "--filter=blob:limit=2m",
            "--no-tags",
            "--single-branch",
            "--",
            url,
            str(target),
        ]
        try:
            subprocess.run(
                command,
                check=True,
                timeout=120,
                env=environment,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
            )
            commit_sha = subprocess.run(
                ["git", "-C", str(target), "rev-parse", "HEAD"],
                check=True,
                timeout=10,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
            ).stdout.strip()
            file_count, byte_count = self._measure(target)
            return FetchedRepository(target, commit_sha, file_count, byte_count)
        except (subprocess.SubprocessError, OSError, GitHubAnalysisError) as error:
            if target.exists():
                shutil.rmtree(target)
            raise GitHubAnalysisError("只读拉取失败；请检查地址、网络或私有仓库令牌") from error

    @staticmethod
    def _measure(root: Path) -> tuple[int, int]:
        file_count = 0
        byte_count = 0
        for path in root.rglob("*"):
            if path.is_symlink() or not path.is_file():
                continue
            byte_count += path.stat().st_size
            if byte_count > MAX_BYTES:
                raise GitHubAnalysisError("仓库超过 5,000 文件或 100 MiB 的安全上限")
            if ".git" in path.parts:
                continue
            file_count += 1
            if file_count > MAX_FILES:
                raise GitHubAnalysisError("仓库超过 5,000 文件或 100 MiB 的安全上限")
        return file_count, byte_count


def _read_text(path: Path) -> str:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_TEXT_BYTES:
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _git_activity(root: Path) -> list[dict[str, str]]:
    try:
        output = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "log",
                "-20",
                "--date=iso-strict",
                "--pretty=format:%H%x1f%aI%x1f%an%x1f%s%x1e",
            ],
            check=True,
            timeout=10,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return []
    activity: list[dict[str, str]] = []
    for record in output.split("\x1e"):
        fields = record.strip().split("\x1f")
        if len(fields) == 4:
            activity.append(
                {
                    "commit_sha": fields[0],
                    "authored_at": fields[1],
                    "author": fields[2],
                    "title": fields[3],
                }
            )
    return activity


def analyze_repository(root: Path) -> tuple[dict[str, Any], str | None, dict[str, Any]]:
    files = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink() and ".git" not in path.parts
    )
    readme_path = next(
        (root / item for item in files if Path(item).name.casefold().startswith("readme")), None
    )
    readme = _read_text(readme_path) if readme_path else ""
    readme_sha = hashlib.sha256(readme_path.read_bytes()).hexdigest() if readme_path else None
    dependency_names = {
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "go.mod",
        "Cargo.toml",
        "pom.xml",
        "build.gradle",
    }
    dependencies = [item for item in files if Path(item).name in dependency_names]
    test_paths = [
        item
        for item in files
        if "test" in Path(item).name.casefold() or "tests" in Path(item).parts
    ]
    deploy_names = {
        "Dockerfile",
        "docker-compose.yml",
        "compose.yml",
        "vercel.json",
        "netlify.toml",
    }
    deployment = [
        item
        for item in files
        if Path(item).name in deploy_names or item.startswith(".github/workflows/")
    ]
    extension_map = {
        ".py": "Python",
        ".ts": "TypeScript",
        ".tsx": "React/TypeScript",
        ".js": "JavaScript",
        ".rs": "Rust",
        ".go": "Go",
        ".java": "Java",
    }
    stack = sorted(
        {extension_map[Path(item).suffix] for item in files if Path(item).suffix in extension_map}
    )
    top_level = sorted({item.split("/", 1)[0] for item in files})[:30]
    outcome_lines = [
        line.strip()
        for line in readme.splitlines()
        if any(token in line.casefold() for token in ("%", "users", "性能", "用户", "提升", "减少"))
    ][:12]
    risks: list[str] = []
    if not readme:
        risks.append("未找到可读取的 README")
    if not test_paths:
        risks.append("未发现明显的测试目录或测试文件")
    if not dependencies:
        risks.append("未发现常见依赖清单")
    profile = {
        "summary": readme[:2_000],
        "directory_structure": top_level,
        "dependency_manifests": dependencies,
        "key_modules": [item for item in files if Path(item).suffix in extension_map][:40],
        "technology_stack": stack,
        "tests": test_paths[:40],
        "deployment": deployment[:40],
        "recent_activity": _git_activity(root),
        "outcome_clues": outcome_lines,
        "risk_notes": risks,
    }
    provenance = {
        "readme": readme_path.relative_to(root).as_posix() if readme_path else None,
        "analyzed_files": files[:200],
        "analyzer": "ach-github-static-v1",
    }
    return profile, readme_sha, provenance


class GitHubProjectService:
    def __init__(
        self,
        engine: Engine,
        cache_root: Path,
        secrets: WritableSecretStore,
        fetcher: RepositoryFetcher | None = None,
    ) -> None:
        self.engine = engine
        self.cache_root = cache_root
        self.secrets = secrets
        self.fetcher = fetcher or GitCliRepositoryFetcher()

    def save_token(self, token: str) -> dict[str, bool]:
        self.secrets.set("github/read-token", token)
        return {"configured": True}

    def token_status(self) -> dict[str, bool]:
        return {"configured": self.secrets.get("github/read-token") is not None}

    def analyze(self, raw_url: str, use_private_token: bool) -> dict[str, Any]:
        url, owner, repository = normalize_github_url(raw_url)
        secret = self.secrets.get("github/read-token") if use_private_token else None
        if use_private_token and secret is None:
            raise GitHubAnalysisError("尚未配置 GitHub 只读令牌")
        fetched = self.fetcher.fetch(url, self.cache_root, secret.reveal() if secret else None)
        profile, readme_sha, provenance = analyze_repository(fetched.root)
        cache_key = hashlib.sha256(url.encode()).hexdigest()
        project_id = f"github_{hashlib.sha256(url.encode()).hexdigest()[:24]}"
        analysis_digest = hashlib.sha256((url + fetched.commit_sha).encode()).hexdigest()
        analysis_id = f"github_analysis_{analysis_digest[:32]}"
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            connection.execute(
                text("INSERT OR IGNORE INTO project_identity (project_id) VALUES (:project_id)"),
                {"project_id": project_id},
            )
            connection.execute(
                text("""INSERT OR IGNORE INTO project_record
                (project_id, revision, schema_version, display_name,
                 root_locator, created_at, created_by)
                VALUES (:project_id, 1, 1, :display_name, :root_locator, :created_at, 'user')"""),
                {
                    "project_id": project_id,
                    "display_name": f"{owner}/{repository}",
                    "root_locator": str(fetched.root),
                    "created_at": now,
                },
            )
            connection.execute(
                text("""INSERT OR IGNORE INTO github_project_analysis
                (analysis_id, project_id, repository_url, owner, repository, commit_sha, cache_key,
                 fetched_at, file_count, byte_count, readme_sha256, profile, provenance)
                VALUES (:analysis_id, :project_id, :repository_url, :owner,
                 :repository, :commit_sha, :cache_key, :fetched_at, :file_count,
                 :byte_count, :readme_sha256, :profile, :provenance)"""),
                {
                    "analysis_id": analysis_id,
                    "project_id": project_id,
                    "repository_url": url,
                    "owner": owner,
                    "repository": repository,
                    "commit_sha": fetched.commit_sha,
                    "cache_key": cache_key,
                    "fetched_at": now,
                    "file_count": fetched.file_count,
                    "byte_count": fetched.byte_count,
                    "readme_sha256": readme_sha,
                    "profile": json.dumps(profile, ensure_ascii=False),
                    "provenance": json.dumps(provenance, ensure_ascii=False),
                },
            )
        return self.get_analysis(analysis_id)

    def get_analysis(self, analysis_id: str) -> dict[str, Any]:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text("SELECT * FROM github_project_analysis WHERE analysis_id = :analysis_id"),
                    {"analysis_id": analysis_id},
                )
                .mappings()
                .first()
            )
            if row is None:
                raise LookupError("GitHub 项目分析不存在")
            return self._decode_row(dict(row))

    def list_for_project(self, project_id: str) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            return [
                self._decode_row(dict(row))
                for row in connection.execute(
                    text(
                        "SELECT * FROM github_project_analysis "
                        "WHERE project_id = :project_id "
                        "ORDER BY fetched_at DESC, analysis_id"
                    ),
                    {"project_id": project_id},
                ).mappings()
            ]

    @staticmethod
    def _decode_row(row: dict[str, Any]) -> dict[str, Any]:
        for field in ("profile", "provenance"):
            value = row.get(field)
            if isinstance(value, str):
                row[field] = json.loads(value)
        return row
