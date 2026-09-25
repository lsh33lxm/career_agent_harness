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

MEITU_NEXT_HTML = '''<script>{"initJobList":[
{"jobId":"campus-1","title":"AI产品实习生","departmentName":"研发团队","locations":"北京市",
"publishedAt":"2026-09-24","modeName":"实习生招聘","siteId":"141055"},
{"jobId":"social-1","title":"社会招聘岗位","departmentName":"研发团队","locations":"北京市",
"publishedAt":"2026-09-24","modeName":"社会招聘","siteId":"54137"}],"initTotal":2}</script>'''


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


def test_meitu_ssr_list_parses_only_campus_and_intern_jobs() -> None:
    source = OfficialCampusJobSource(MEITU_CAMPUS, fixture_html=MEITU_NEXT_HTML)
    records = source.search("")
    assert len(records) == 1
    normalized = source.normalize(records[0])
    assert normalized.title == "AI产品实习生"
    assert normalized.company == "美图"
    assert normalized.location == "北京市"
    assert normalized.source_url == "https://campus.meitu.com/jobIntern/campus-1"
    assert normalized.published_at is not None


def test_meitu_ssr_list_query_filters_public_fields() -> None:
    source = OfficialCampusJobSource(MEITU_CAMPUS, fixture_html=MEITU_NEXT_HTML)
    assert len(source.search("研发团队")) == 1
    assert source.search("社会招聘") == ()


def test_meitu_detail_does_not_promote_homepage_first_record() -> None:
    source = OfficialCampusJobSource(MEITU_CAMPUS, fixture_html=MEITU_NEXT_HTML)
    with pytest.raises(KeyError, match="岗位详情"):
        source.fetch_detail("https://campus.meitu.com/jobIntern/not-in-list")


def test_meitu_ssr_detail_preserves_rendered_jd_and_metadata() -> None:
    detail_html = '''
    <div class="banner_jobTitle__x">海外市场运营实习生</div>
    <span class="banner_metaLabel__x">招聘类型<!-- -->:</span>
    <span class="banner_metaValue__x">校园招聘</span>
    <span class="banner_metaLabel__x">工作地点<!-- -->:</span>
    <span class="banner_metaValue__x">广东深圳市</span>
    <span class="banner_metaLabel__x">发布日期<!-- -->:</span>
    <span class="banner_metaValue__x">2026-08-12</span>
    <div class="content_sectionTitle__x">职位描述</div>
    <div class="content_sectionContent__x"><div>
      <p>【岗位职责】</p><p>1.参与活动策划</p>
      <p>【任职要求】</p><p>2.熟悉日语</p>
    </div></div>
    '''
    source = OfficialCampusJobSource(MEITU_CAMPUS, fixture_html=detail_html)
    raw = source.fetch_detail("https://hr.meitu.com/jobCampus/detail-1")
    normalized = source.normalize(raw)
    assert normalized.title == "海外市场运营实习生"
    assert normalized.location == "广东深圳市"
    assert normalized.published_at is not None
    assert normalized.requirements == ("2.熟悉日语",)


def test_tencent_public_api_search_and_detail_preserve_full_jd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = OfficialCampusJobSource(TENCENT_CAMPUS)
    def fake_fetch(path: str, *, payload: dict[str, object] | None = None) -> dict[str, object]:
        if path.startswith("/api/v1/position/searchPosition"):
            return {"status": 0, "data": {"positionList": [{
                "postId": "post-1", "positionTitle": "AI工程师", "workCities": "深圳",
                "projectName": "应届毕业生", "projectId": 1, "position": 783,
            }]}}
        return {"status": 0, "data": {"postId": "post-1", "title": "AI工程师",
            "workCityList": ["深圳"], "desc": "负责AI系统开发", "request": "熟悉 Python\n了解 RAG"}}
    monkeypatch.setattr(source, "_fetch_tencent_json", fake_fetch)
    raw = source.search("AI")[0]
    assert raw.source_ref.endswith("postId=post-1")
    detail = source.fetch_detail(raw.source_ref)
    normalized = source.normalize(detail)
    assert normalized.title == "AI工程师"
    assert normalized.requirements == ("熟悉 Python", "了解 RAG")
    assert source.search("不存在的岗位") == ()


def test_tencent_api_search_deduplicates_post_ids_and_marks_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = OfficialCampusJobSource(TENCENT_CAMPUS)
    calls = 0

    def fake_fetch(path: str, *, payload: dict[str, object] | None = None) -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == 1:
            row = {"postId": "same", "positionTitle": "AI工程师", "workCities": "深圳"}
            return {"status": 0, "data": {"positionList": [row, row]}}
        raise OfficialSourceError("模拟网络失败")

    monkeypatch.setattr(source, "_fetch_tencent_json", fake_fetch)
    assert len(source.search("AI")) == 1
    assert source.health().status == "ok"
    with pytest.raises(OfficialSourceError, match="模拟网络失败"):
        source.search("AI")
    assert source.health().status == "error"
