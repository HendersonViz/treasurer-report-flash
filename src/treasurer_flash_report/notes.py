from __future__ import annotations

import re
from html import escape
from pathlib import Path

try:
    from markdown_it import MarkdownIt
except ModuleNotFoundError:  # pragma: no cover - exercised when optional dep is absent locally
    MarkdownIt = None  # type: ignore[assignment]


def read_notes_content(notes_path: Path | None) -> str:
    if notes_path is None:
        return ""
    return notes_path.read_text(encoding="utf-8")


def extract_named_markdown_section(
    markdown: str, heading_names: set[str]
) -> tuple[str, str]:
    if not markdown.strip():
        return "", ""

    lines = markdown.splitlines()
    start_idx: int | None = None
    start_level = 0
    end_idx = len(lines)

    for idx, line in enumerate(lines):
        parsed = _parse_heading(line)
        if parsed is None:
            continue
        level, heading = parsed
        if _normalize_heading(heading) in heading_names:
            start_idx = idx
            start_level = level
            break

    if start_idx is None:
        return "", markdown

    for idx in range(start_idx + 1, len(lines)):
        parsed = _parse_heading(lines[idx])
        if parsed is None:
            continue
        level, _ = parsed
        if level <= start_level:
            end_idx = idx
            break

    section = "\n".join(lines[start_idx + 1 : end_idx]).strip()
    remaining = "\n".join([*lines[:start_idx], *lines[end_idx:]]).strip()
    return section, remaining


def extract_plain_notes(markdown: str) -> list[str]:
    notes: list[str] = []
    current: list[str] = []

    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                notes.append(" ".join(current))
                current = []
            continue

        stripped = stripped.lstrip("#").strip()
        stripped = _strip_markdown_emphasis(stripped)
        if stripped.startswith(("- ", "* ")):
            if current:
                notes.append(" ".join(current))
                current = []
            notes.append(_strip_markdown_emphasis(stripped[2:].strip()))
            continue
        if len(stripped) > 3 and stripped[0].isdigit() and stripped[1:3] in {". ", ") "}:
            if current:
                notes.append(" ".join(current))
                current = []
            notes.append(_strip_markdown_emphasis(stripped[3:].strip()))
            continue

        current.append(stripped)

    if current:
        notes.append(" ".join(current))

    return [note for note in notes if note]


def render_safe_markdown(markdown: str) -> str:
    if not markdown.strip():
        return ""

    if MarkdownIt is not None:
        renderer = MarkdownIt("commonmark", {"html": False, "linkify": False})
        return renderer.render(markdown)

    return _render_minimal_markdown(markdown)


def render_notes_fallback(notes: list[str], empty_message: str) -> str:
    source = notes or [empty_message]
    return "<ul>" + "".join(f"<li>{escape(note)}</li>" for note in source) + "</ul>"


def _strip_markdown_emphasis(text: str) -> str:
    replacements = {
        "**": "",
        "__": "",
        "*": "",
        "_": "",
        "`": "",
    }
    for marker, replacement in replacements.items():
        text = text.replace(marker, replacement)
    return text


def _parse_heading(line: str) -> tuple[int, str] | None:
    stripped = line.strip()
    level = len(stripped) - len(stripped.lstrip("#"))
    if not 1 <= level <= 6:
        return None
    if stripped[level : level + 1] != " ":
        return None
    return level, stripped[level:].strip()


def _normalize_heading(heading: str) -> str:
    return re.sub(r"\s+", " ", _strip_markdown_emphasis(heading).strip().lower())


def _render_minimal_markdown(markdown: str) -> str:
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(f"<p>{_inline_markdown(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_list() -> None:
        if list_items:
            blocks.append("<ul>" + "".join(list_items) + "</ul>")
            list_items.clear()

    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            flush_list()
            continue

        heading_level = len(stripped) - len(stripped.lstrip("#"))
        if 1 <= heading_level <= 3 and stripped[heading_level : heading_level + 1] == " ":
            flush_paragraph()
            flush_list()
            text = stripped[heading_level:].strip()
            blocks.append(f"<h{heading_level}>{_inline_markdown(text)}</h{heading_level}>")
            continue

        if stripped.startswith(("- ", "* ")):
            flush_paragraph()
            list_items.append(f"<li>{_inline_markdown(stripped[2:].strip())}</li>")
            continue

        paragraph.append(stripped)

    flush_paragraph()
    flush_list()
    return "".join(blocks)


def _inline_markdown(text: str) -> str:
    escaped = escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"__(.+?)__", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", escaped)
    escaped = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"<em>\1</em>", escaped)
    return re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', escaped)
