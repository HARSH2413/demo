"""Lightweight, format-aware parent/child chunk construction.

The module deliberately uses deterministic signals already present in extracted
text (Word headings, spreadsheet sheet markers, and text rows).  It does not
invoke an LLM, OCR, or a vision model, which keeps ingestion practical on
CPU-only machines.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable


_MARKDOWN_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_NUMBERED_HEADING = re.compile(r"^\d+(?:\.\d+)*[.)]?\s+\S+")
_SHEET_MARKER = re.compile(r"^--- Sheet:\s*(.+?)\s*---$")


@dataclass(frozen=True)
class ParentSection:
    """A logical parent whose children are stored as searchable chunks."""

    parent_id: str
    title: str
    path: tuple[str, ...]
    content: str
    block_type: str = "section"


@dataclass(frozen=True)
class ChildChunk:
    """A retrieval-sized child and the metadata required to reassemble it."""

    content: str
    parent_id: str
    parent_title: str
    section_path: tuple[str, ...]
    block_type: str
    child_index: int

    def metadata(self) -> dict[str, Any]:
        return {
            "chunk_kind": "child",
            "parent_id": self.parent_id,
            "parent_title": self.parent_title,
            "section_path": list(self.section_path),
            "block_type": self.block_type,
            "child_index_in_parent": self.child_index,
        }


class HierarchicalChunker:
    """Creates cheap logical parents and embedding-ready children.

    Parents are represented in child metadata instead of being embedded.  This
    keeps vector count and RAM use close to the prior flat pipeline while
    letting retrieval safely expand only sibling chunks from the same section.
    """

    def __init__(self, chunk_size: int):
        self.chunk_size = chunk_size

    def build_children(self, text: str, file_type: str, splitter: Any) -> list[ChildChunk]:
        sections = self._sections(text, file_type)
        children: list[ChildChunk] = []
        for section in sections:
            if section.block_type in {"table_rows", "spreadsheet_rows"}:
                pieces = list(self._group_rows(section.content))
            else:
                pieces = splitter.split_text(section.content)

            for index, piece in enumerate(pieces):
                clean_piece = piece.strip()
                if clean_piece:
                    children.append(
                        ChildChunk(
                            content=clean_piece,
                            parent_id=section.parent_id,
                            parent_title=section.title,
                            section_path=section.path,
                            block_type=section.block_type,
                            child_index=index,
                        )
                    )
        return children

    def _sections(self, text: str, file_type: str) -> list[ParentSection]:
        if file_type == "Word Document":
            return self._heading_sections(text)
        if file_type == "Excel Spreadsheet":
            return self._sheet_sections(text)
        if file_type == "CSV Spreadsheet":
            return [self._section("dataset-1", "Dataset", ("Dataset",), text, "spreadsheet_rows")]
        if file_type == "Text File":
            return self._text_sections(text)
        return [self._section("section-1", "Document", ("Document",), text, "section")]

    def _heading_sections(self, text: str) -> list[ParentSection]:
        sections: list[ParentSection] = []
        current_lines: list[str] = []
        heading_stack: list[str] = []
        current_title = "Document"
        ordinal = 0

        def flush() -> None:
            nonlocal ordinal, current_lines
            body = "\n".join(current_lines).strip()
            if body:
                ordinal += 1
                path = tuple(heading_stack) if heading_stack else (current_title,)
                sections.append(self._section(f"section-{ordinal}", current_title, path, body, "section"))
            current_lines = []

        for line in text.splitlines():
            match = _MARKDOWN_HEADING.match(line)
            if not match:
                current_lines.append(line)
                continue
            flush()
            level = len(match.group(1))
            current_title = match.group(2).strip()
            heading_stack = heading_stack[: level - 1]
            heading_stack.append(current_title)
            # Preserve the heading in the parent's text for lexical retrieval.
            current_lines.append(line)
        flush()
        return sections or [self._section("section-1", "Document", ("Document",), text, "section")]

    def _sheet_sections(self, text: str) -> list[ParentSection]:
        sections: list[ParentSection] = []
        lines: list[str] = []
        title = "Workbook"
        ordinal = 0

        def flush() -> None:
            nonlocal ordinal, lines
            body = "\n".join(lines).strip()
            if body:
                ordinal += 1
                sections.append(self._section(f"sheet-{ordinal}", title, (title,), body, "spreadsheet_rows"))
            lines = []

        for line in text.splitlines():
            match = _SHEET_MARKER.match(line)
            if match:
                flush()
                title = match.group(1).strip()
                lines.append(line)
            else:
                lines.append(line)
        flush()
        return sections or [self._section("sheet-1", "Workbook", ("Workbook",), text, "spreadsheet_rows")]

    def _text_sections(self, text: str) -> list[ParentSection]:
        # Markdown and numbered headings are common in exported plain text.
        lines = text.splitlines()
        normalized = []
        for line in lines:
            if _NUMBERED_HEADING.match(line) and len(line) < 120:
                normalized.append(f"## {line}")
            else:
                normalized.append(line)
        return self._heading_sections("\n".join(normalized))

    def _group_rows(self, content: str) -> Iterable[str]:
        """Group complete rows without splitting a row in two."""
        rows = [row for row in content.splitlines() if row.strip()]
        if not rows:
            return
        group: list[str] = []
        length = 0
        for row in rows:
            projected = length + len(row) + (1 if group else 0)
            if group and projected > self.chunk_size:
                yield "\n".join(group)
                group, length = [], 0
            group.append(row)
            length += len(row) + (1 if length else 0)
        if group:
            yield "\n".join(group)

    @staticmethod
    def _section(parent_id: str, title: str, path: tuple[str, ...], content: str, block_type: str) -> ParentSection:
        return ParentSection(parent_id=parent_id, title=title, path=path, content=content, block_type=block_type)
