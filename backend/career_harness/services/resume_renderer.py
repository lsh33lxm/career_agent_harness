from __future__ import annotations

import html
import re
from collections.abc import Iterable
from typing import Any

TEMPLATE_ID = "resume-render-html"
TEMPLATE_VERSION = "1.0.0"
TEMPLATE_DESCRIPTION = "Agent Career Harness owned warm-paper HTML/CSS resume template"
TEMPLATE_CSS = """
:root { color-scheme: light; font-family: Georgia, 'Times New Roman', serif; }
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
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title><style>{TEMPLATE_CSS}</style></head>"
        f"<body><article class=\"resume\">{''.join(sections)}</article></body></html>"
    )


def _pdf_escape(line: str) -> str:
    # Helvetica is intentionally used as a dependency-free baseline. Non-Latin glyphs
    # are replaced rather than allowing malformed PDF bytes; the HTML preview preserves them.
    safe = line.encode("latin-1", errors="replace").decode("latin-1")
    return safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def render_pdf(content: dict[str, Any]) -> tuple[bytes, int]:
    lines = resume_lines(content)
    per_page = 42
    pages = [lines[offset : offset + per_page] for offset in range(0, len(lines), per_page)]
    pages = pages or [["Resume content is empty"]]
    objects: list[bytes] = []

    def add(value: str) -> int:
        objects.append(value.encode("latin-1", errors="replace"))
        return len(objects)

    catalog_id = add("")
    pages_id = add("")
    font_id = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids: list[int] = []
    for page_lines in pages:
        stream_lines = ["BT", "/F1 10 Tf", "50 742 Td"]
        for index, line in enumerate(page_lines):
            if index:
                stream_lines.append("0 -17 Td")
            stream_lines.append(f"({_pdf_escape(line)}) Tj")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines).encode("latin-1", errors="replace")
        content_id = add(
            f"<< /Length {len(stream)} >>\nstream\n"
            + stream.decode("latin-1")
            + "\nendstream"
        )
        page_ids.append(
            add(
                f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            )
        )
    objects[catalog_id - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode()
    objects[pages_id - 1] = (
        f"<< /Type /Pages /Kids [{' '.join(f'{page} 0 R' for page in page_ids)}] "
        f"/Count {len(page_ids)} >>"
    ).encode()
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode())
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(output), len(pages)


def keyword_gaps(content: dict[str, Any], requirement_texts: Iterable[str]) -> tuple[str, ...]:
    haystack = " ".join(resume_lines(content)).lower()
    gaps: list[str] = []
    for text in requirement_texts:
        normalized = re.sub(r"\s+", " ", text).strip()
        if normalized and normalized.lower() not in haystack:
            gaps.append(normalized)
    return tuple(dict.fromkeys(gaps))
