from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

from career_harness.core.job_source import (
    JobSourceHealth,
    JobSourceTerms,
    JobSourceTermsStatus,
    NormalizedJobRecord,
    RawJobRecord,
)


class OfficialSourceError(RuntimeError):
    """A bounded, user-visible failure while reading an official source."""


@dataclass(frozen=True, slots=True)
class OfficialSourceConfig:
    source_id: str
    company: str
    landing_url: str
    allowed_hosts: frozenset[str]
    license_note: str
    max_pages: int = 3
    timeout_seconds: float = 12.0
    max_response_bytes: int = 2_000_000


def _host_allowed(url: str, allowed_hosts: frozenset[str]) -> bool:
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return host in allowed_hosts


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", unescape(str(value))).strip()
    return text or None


def _jsonld_objects(html: str) -> tuple[dict[str, Any], ...]:
    objects: list[dict[str, Any]] = []
    for raw in re.findall(
        r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        try:
            decoded = json.loads(unescape(raw).strip())
        except json.JSONDecodeError:
            continue
        values = decoded if isinstance(decoded, list) else [decoded]
        for value in values:
            if not isinstance(value, dict):
                continue
            item_type = value.get("@type")
            if item_type == "JobPosting" or (
                isinstance(item_type, list) and "JobPosting" in item_type
            ):
                objects.append(value)
            elif isinstance(value.get("@graph"), list):
                objects.extend(
                    item
                    for item in value["@graph"]
                    if isinstance(item, dict) and item.get("@type") == "JobPosting"
                )
    return tuple(objects)


def _html_links(html: str, base_url: str, allowed_hosts: frozenset[str]) -> tuple[str, ...]:
    links: list[str] = []
    for href in re.findall(r"<a[^>]+href=[\"']([^\"']+)[\"']", html, flags=re.IGNORECASE):
        absolute = urljoin(base_url, unescape(href).strip())
        if (
            _host_allowed(absolute, allowed_hosts)
            and re.search(r"(job|position|recruit|校园|职位|岗位)", absolute, re.IGNORECASE)
            and absolute not in links
        ):
            links.append(absolute)
    return tuple(links)


def _requirements(description: str | None) -> tuple[str, ...]:
    if not description:
        return ()
    lines = [
        _clean_text(line.lstrip("-•* "))
        for line in re.split(r"(?:<br\s*/?>|\n|\r)+", description)
    ]
    return tuple(line for line in lines if line and len(line) <= 1000)[:80]


class OfficialCampusJobSource:
    """Read-only JSON-LD/HTML adapter for a public corporate campus site."""

    def __init__(self, config: OfficialSourceConfig, *, fixture_html: str | None = None) -> None:
        self.config = config
        self.source_id = config.source_id
        self._fixture_html = fixture_html
        self._last_health = JobSourceHealth(status="ok", message="尚未执行现场检查")

    def _fetch(self, url: str) -> tuple[str, str]:
        if not _host_allowed(url, self.config.allowed_hosts):
            raise OfficialSourceError("官方来源链接不在允许域名内")
        request = Request(
            url,
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "User-Agent": "AgentCareerHarness/0.1 (read-only campus source)",
            },
        )
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:  # noqa: S310
                final_url = response.geturl()
                if not _host_allowed(final_url, self.config.allowed_hosts):
                    raise OfficialSourceError("官方来源发生越界跳转，已拒绝读取")
                chunks: list[bytes] = []
                total = 0
                while True:
                    chunk = response.read(min(64 * 1024, self.config.max_response_bytes - total))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total += len(chunk)
                    if total >= self.config.max_response_bytes:
                        raise OfficialSourceError("官方来源响应超过大小上限")
                charset = response.headers.get_content_charset() or "utf-8"
                return b"".join(chunks).decode(charset, errors="replace"), final_url
        except (HTTPError, URLError, TimeoutError) as error:
            raise OfficialSourceError(f"官方来源暂时不可访问：{error}") from error

    def _parse(self, html: str, page_url: str) -> tuple[RawJobRecord, ...]:
        captured_at = datetime.now(UTC)
        records: list[RawJobRecord] = []
        for item in _jsonld_objects(html):
            title = _clean_text(item.get("title"))
            if not title:
                continue
            company = item.get("hiringOrganization")
            if isinstance(company, dict):
                company = company.get("name")
            location = item.get("jobLocation")
            if isinstance(location, list):
                location = location[0] if location else None
            if isinstance(location, dict):
                address = location.get("address") or {}
                location = address.get("addressLocality") or address.get("streetAddress")
            source_url = _clean_text(item.get("url")) or page_url
            if not _host_allowed(source_url, self.config.allowed_hosts):
                source_url = page_url
            payload = {
                "title": title,
                "company": _clean_text(company) or self.config.company,
                "location": _clean_text(location),
                "employment_type": _clean_text(item.get("employmentType")),
                "published_at": _clean_text(item.get("datePosted")),
                "updated_at": _clean_text(item.get("dateModified")),
                "description": (
                    unescape(str(item.get("description"))).strip()
                    if item.get("description") is not None
                    else None
                ),
                "source_url": source_url,
                "source_platform": self.config.source_id,
            }
            records.append(
                RawJobRecord(
                    source_ref=source_url,
                    raw_text=json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    captured_at=captured_at,
                )
            )
        if records:
            return tuple(records)
        return tuple(
            RawJobRecord(
                source_ref=url,
                raw_text=json.dumps({"source_url": url}),
                captured_at=captured_at,
            )
            for url in _html_links(html, page_url, self.config.allowed_hosts)[
                : self.config.max_pages
            ]
        )

    def search(self, query: str) -> tuple[RawJobRecord, ...]:
        html = self._fixture_html
        page_url = self.config.landing_url
        if html is None:
            html, page_url = self._fetch(self.config.landing_url)
        records = self._parse(html, page_url)
        term = query.strip().casefold()
        if not term:
            self._last_health = JobSourceHealth(
                status="ok", message=f"官方页面读取成功，发现 {len(records)} 条记录"
            )
            return records
        filtered = tuple(item for item in records if term in item.raw_text.casefold())
        self._last_health = JobSourceHealth(
            status="ok", message=f"官方页面读取成功，匹配 {len(filtered)} 条记录"
        )
        return filtered

    def fetch_detail(self, ref: str) -> RawJobRecord:
        if not _host_allowed(ref, self.config.allowed_hosts):
            raise OfficialSourceError("官方来源链接不在允许域名内")
        if self._fixture_html is not None:
            html, page_url = self._fixture_html, ref
        else:
            html, page_url = self._fetch(ref)
        records = self._parse(html, page_url)
        if records:
            return records[0]
        raise KeyError("官方来源未返回可识别的岗位详情")

    def normalize(self, raw: RawJobRecord) -> NormalizedJobRecord:
        try:
            data = json.loads(raw.raw_text)
        except json.JSONDecodeError as error:
            raise OfficialSourceError("官方来源返回内容不是可识别的 JSON-LD 岗位") from error
        title = _clean_text(data.get("title"))
        if not title:
            raise OfficialSourceError("官方来源岗位缺少职位名称")
        published = data.get("published_at")
        published_at = (
            datetime.fromisoformat(published.replace("Z", "+00:00")) if published else None
        )
        return NormalizedJobRecord(
            title=title,
            company=_clean_text(data.get("company")) or self.config.company,
            location=_clean_text(data.get("location")),
            published_at=published_at,
            requirements=_requirements(data.get("description")),
            source_url=_clean_text(data.get("source_url")) or raw.source_ref,
        )

    def health(self) -> JobSourceHealth:
        return self._last_health

    def terms(self) -> JobSourceTerms:
        return JobSourceTerms(
            source_id=self.source_id,
            status=JobSourceTermsStatus.VERIFIED,
            note=self.config.license_note,
        )


TENCENT_CAMPUS = OfficialSourceConfig(
    source_id="official-cn-tencent-campus",
    company="腾讯",
    landing_url="https://join.qq.com/",
    allowed_hosts=frozenset({"join.qq.com", "cdn.multilingualres.hr.tencent.com"}),
    license_note="腾讯官方校招站公开页面；仅人工触发的只读访问，不提交表单或绕过验证。",
)

MEITU_CAMPUS = OfficialSourceConfig(
    source_id="official-cn-meitu-campus",
    company="美图",
    landing_url="https://campus.meitu.com/",
    allowed_hosts=frozenset({"campus.meitu.com", "hr.meitu.com"}),
    license_note="美图官方校招站公开页面；仅人工触发的只读访问，不提交表单或绕过验证。",
)


def official_source(source_id: str, *, fixture_html: str | None = None) -> OfficialCampusJobSource:
    configs = {TENCENT_CAMPUS.source_id: TENCENT_CAMPUS, MEITU_CAMPUS.source_id: MEITU_CAMPUS}
    try:
        return OfficialCampusJobSource(configs[source_id], fixture_html=fixture_html)
    except KeyError as error:
        raise ValueError(f"不支持的官方岗位来源：{source_id}") from error
