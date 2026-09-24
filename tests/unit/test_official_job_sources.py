from __future__ import annotations

import pytest

from career_harness.adapters.official_job_sources import (
    MEITU_CAMPUS,
    TENCENT_CAMPUS,
    OfficialCampusJobSource,
    OfficialSourceError,
)

HTML = """
<html><body>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"JobPosting","title":"AI Agent 实习生",
"datePosted":"2026-09-20","hiringOrganization":{"name":"腾讯"},
"jobLocation":{"address":{"addressLocality":"深圳"}},
"employmentType":"INTERN","url":"https://join.qq.com/job/123",
"description":"岗位职责：参与 Agent 工程\\n- 熟悉 Python\\n- 了解 RAG"}
</script>
<a href="/job/123">岗位详情</a>
</body></html>
"""


def test_tencent_fixture_search_normalizes_full_description_and_provenance() -> None:
    source = OfficialCampusJobSource(TENCENT_CAMPUS, fixture_html=HTML)
    raw = source.search("Agent")[0]
    normalized = source.normalize(raw)
    assert normalized.title == "AI Agent 实习生"
    assert normalized.company == "腾讯"
    assert normalized.location == "深圳"
    assert normalized.source_url == "https://join.qq.com/job/123"
    assert normalized.requirements == ()
    assert source.terms().status.value == "verified"


def test_empty_official_page_is_a_successful_empty_snapshot() -> None:
    source = OfficialCampusJobSource(
        MEITU_CAMPUS, fixture_html="<html><body>暂无职位</body></html>"
    )
    assert source.search("") == ()
    assert source.health().status == "ok"


def test_requirement_parser_excludes_duties_after_explicit_section() -> None:
    fixture = """
    <script type="application/ld+json">
    {"@type":"JobPosting","title":"后端实习生",
     "hiringOrganization":{"name":"示例公司"},
     "description":"岗位职责\\n- 参与服务开发\\n- 编写测试\\n任职要求\\n- 熟悉 Python\\n- 了解 SQL",
     "url":"https://join.qq.com/job/requirements"}
    </script>
    """
    source = OfficialCampusJobSource(TENCENT_CAMPUS, fixture_html=fixture)
    normalized = source.normalize(source.search("")[0])
    assert normalized.requirements == ("熟悉 Python", "了解 SQL")


def test_query_filters_without_inventing_unknown_fields() -> None:
    source = OfficialCampusJobSource(TENCENT_CAMPUS, fixture_html=HTML)
    assert len(source.search("深圳")) == 1
    assert source.search("上海") == ()


def test_detail_rejects_unapproved_host_before_network() -> None:
    source = OfficialCampusJobSource(TENCENT_CAMPUS, fixture_html=HTML)
    with pytest.raises(OfficialSourceError, match="允许域名"):
        source.fetch_detail("https://evil.example/job/1")


def test_missing_jobposting_is_not_promoted_to_a_job() -> None:
    source = OfficialCampusJobSource(TENCENT_CAMPUS, fixture_html='<a href="/job/1">岗位</a>')
    raw = source.search("")[0]
    with pytest.raises(OfficialSourceError, match="缺少职位名称|不是可识别"):
        source.normalize(raw)
