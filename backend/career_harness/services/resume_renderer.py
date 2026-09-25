from __future__ import annotations

import html
import os
import re
from collections.abc import Iterable
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

TEMPLATE_ID = "resume-render-html"
TEMPLATE_VERSION = "1.0.0"
TEMPLATE_DESCRIPTION = "Agent Career Harness owned warm-paper HTML/CSS resume template"
TEMPLATE_CSS = """
:root {
  color-scheme: light;
  font-family: Georgia, 'Times New Roman', 'Noto Sans SC', 'Microsoft YaHei', SimHei, sans-serif;
}
body { margin: 0; color: #18352f; background: #f7f1e6; }
.resume { width: 760px; margin: 0 auto; padding: 48px 56px; box-sizing: border-box; }
.resume h1 { margin: 0; font-size: 32px; letter-spacing: .02em; }
.resume h2 { margin: 28px 0 8px; border-bottom: 1px solid #c4a265; font-size: 17px; }
.resume p, .resume li { line-height: 1.55; font-size: 13px; }
.resume .muted { color: #63776f; }
.resume ul { padding-left: 20px; }
""".strip()

TEMPLATE_DEFINITION = {"css": TEMPLATE_CSS, "layout": "single-column", "page": "A4"}


def _label(key: str) -> str:
    return key.replace("_", " ").strip().title()


def _flatten(value: Any) -> Iterable[str]:
    if value is None:
        return
    if isinstance(value, str):
        if value.strip():
            yield value.strip()
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (dict, list, tuple)):
                yield _label(str(key))
                yield from _flatten(item)
            else:
                yield f"{_label(str(key))}: {item}"
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            yield from _flatten(item)
        return
    yield str(value)


def resume_lines(content: dict[str, Any]) -> list[str]:
    preferred = ("name", "contact", "summary", "experience", "projects", "skills", "education")
    ordered_keys = [key for key in preferred if key in content]
    ordered_keys.extend(sorted(key for key in content if key not in preferred))
    lines: list[str] = []
    for key in ordered_keys:
        value = content[key]
        if key not in {"name", "contact"}:
            lines.append(_label(key))
        lines.extend(_flatten(value))
    return lines or ["Resume content is empty"]


def render_html(content: dict[str, Any], *, title: str = "Resume") -> str:
    lines = resume_lines(content)
    heading = html.escape(str(content.get("name") or title))
    sections: list[str] = [f"<h1>{heading}</h1>"]
    for line in lines:
        escaped = html.escape(line)
        if line in {_label(key) for key in content if key not in {"name", "contact"}}:
            sections.append(f"<h2>{escaped}</h2>")
        else:
            sections.append(f"<p>{escaped}</p>")
    return (
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title><style>{TEMPLATE_CSS}</style></head>"
        f"<body><article class=\"resume\">{''.join(sections)}</article></body></html>"
    )


def _find_cjk_font() -> Path | None:
    configured = os.environ.get("ACH_CJK_FONT_PATH")
    candidates = [Path(configured)] if configured else []
    windows_dir = Path(os.environ.get("WINDIR", "C:/Windows"))
    candidates.extend(
        (
            windows_dir / "Fonts" / "NotoSansSC-VF.ttf",
            windows_dir / "Fonts" / "simhei.ttf",
        )
    )
    candidates.extend(
        (
            Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttf"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf"),
        )
    )
    for path in candidates:
        if path.suffix.lower() in {".ttf", ".otf"} and path.is_file():
            return path
    return None


def render_pdf(content: dict[str, Any]) -> tuple[bytes, int]:
    lines = resume_lines(content)
    contains_non_ascii = any(not line.isascii() for line in lines)
    font_name = "Helvetica"
    if contains_non_ascii:
        font_path = _find_cjk_font()
        if font_path is None:
            raise RuntimeError(
                "未找到可用于中文 PDF 的字体。请安装 Noto Sans SC，或通过 "
                "ACH_CJK_FONT_PATH 指定本机 TTF/OTF 字体。"
            )
        font_name = "ACHCJK"
        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
    style = ParagraphStyle(
        "ACHResumeBody",
        fontName=font_name,
        fontSize=10,
        leading=15,
        wordWrap="CJK" if contains_non_ascii else None,
    )
    story = []
    for line in lines:
        story.extend((Paragraph(html.escape(line), style), Spacer(1, 2 * mm)))
    buffer = BytesIO()
    page_count = 0

    def count_page(_canvas: Any, _document: Any) -> None:
        nonlocal page_count
        page_count += 1

    def canvas_factory(*args: Any, **kwargs: Any) -> Canvas:
        kwargs["invariant"] = 1
        return Canvas(*args, **kwargs)

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        pageCompression=0,
        title=str(content.get("name") or "Resume"),
    )
    document.build(
        story,
        onFirstPage=count_page,
        onLaterPages=count_page,
        canvasmaker=canvas_factory,
    )
    return buffer.getvalue(), page_count


def keyword_gaps(content: dict[str, Any], requirement_texts: Iterable[str]) -> tuple[str, ...]:
    haystack = " ".join(resume_lines(content)).lower()
    gaps: list[str] = []
    for text in requirement_texts:
        normalized = re.sub(r"\s+", " ", text).strip()
        if normalized and normalized.lower() not in haystack:
            gaps.append(normalized)
    return tuple(dict.fromkeys(gaps))
