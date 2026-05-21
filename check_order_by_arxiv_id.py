#!/usr/bin/env python3
"""Check that arXiv IDs in README.md table rows are in descending order per section."""

import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

ARXIV_RE = re.compile(r"arxiv:(\d{4}\.\d+)", re.IGNORECASE)
H2_RE = re.compile(r"^## (.+)$")
DEFAULT_README = Path(__file__).resolve().parent / "README.md"

SectionIds = Tuple[str, List[str]]


def is_table_separator(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return False
    cells = [c.strip() for c in stripped.strip("|").split("|")]
    return all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells if cell)


def is_table_data_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and not is_table_separator(stripped)


def arxiv_id_to_sort_key(arxiv_id: str) -> int:
    return int(arxiv_id.replace(".", ""))


def extract_arxiv_id(line: str) -> Optional[str]:
    match = ARXIV_RE.search(line)
    return match.group(1) if match else None


def parse_table_arxiv_ids(lines: List[str]) -> List[str]:
    ids: List[str] = []
    for line in lines:
        if not is_table_data_row(line):
            continue
        arxiv_id = extract_arxiv_id(line)
        if arxiv_id is not None:
            ids.append(arxiv_id)
    return ids


def split_by_h2_sections(lines: List[str]) -> List[SectionIds]:
    """Split file lines into (## heading title, lines in that section)."""
    sections: List[SectionIds] = []
    current_title: Optional[str] = None
    current_lines: List[str] = []

    for line in lines:
        match = H2_RE.match(line.strip())
        if match:
            if current_title is not None:
                sections.append((current_title, current_lines))
            current_title = match.group(1).strip()
            current_lines = []
        elif current_title is not None:
            current_lines.append(line)

    if current_title is not None:
        sections.append((current_title, current_lines))

    return sections


def check_descending_order(ids: List[str]) -> List[Tuple[int, str, str]]:
    """Return (index, current_id, next_id) for each pair that breaks descending order."""
    violations: List[Tuple[int, str, str]] = []
    for i in range(len(ids) - 1):
        current = arxiv_id_to_sort_key(ids[i])
        nxt = arxiv_id_to_sort_key(ids[i + 1])
        if current < nxt:
            violations.append((i, ids[i], ids[i + 1]))
    return violations


def main(argv: Optional[List[str]] = None) -> int:
    path = Path(argv[1]) if argv and len(argv) > 1 else DEFAULT_README
    if not path.is_file():
        print(f"warning: file not found: {path}", file=sys.stderr)
        return 1

    sections = split_by_h2_sections(path.read_text(encoding="utf-8").splitlines())
    if not sections:
        print(
            f"warning: no ## sections found in {path} (nothing to check)",
            file=sys.stderr,
        )
        return 1

    any_ids = False
    all_violations: List[Tuple[str, List[Tuple[int, str, str]]]] = []

    for title, section_lines in sections:
        ids = parse_table_arxiv_ids(section_lines)
        if not ids:
            continue
        any_ids = True
        if len(ids) < 2:
            continue

        violations = check_descending_order(ids)
        if violations:
            all_violations.append((title, violations))

    if not any_ids:
        print(
            f"warning: no arXiv IDs found in table rows of {path}",
            file=sys.stderr,
        )
        return 1

    if all_violations:
        total = sum(len(v) for _, v in all_violations)
        print(
            f"warning: arXiv IDs in {path} are not in descending order "
            f"({total} violation(s) across {len(all_violations)} section(s)):"
        )
        for title, violations in all_violations:
            print(f"  ## {title}")
            for index, current, nxt in violations:
                print(
                    f"    row {index + 1} -> {index + 2}: "
                    f"arXiv:{current} ({arxiv_id_to_sort_key(current)}) "
                    f"< arXiv:{nxt} ({arxiv_id_to_sort_key(nxt)})"
                )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
