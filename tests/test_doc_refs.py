"""Referential-integrity guard for documentation citations (#653).

Docstrings and comments in this package cite docs by filename
(``ARCHITECTURE.md``) and by section (``§4.5``). A doc reorg once left a
trail of dangling citations to deleted files (``docs/ux/pwa.md``,
``theming.md``, ``ACCEPTANCE.md``, …) — this test fails fast when a cite
points at a ``*.md`` file or a ``§N`` section heading that no longer
exists, so the defect class can't recur.

Scope: the package source, the test suite, and ``.pre-commit-config.yaml``
(it carries doc citations too). It is intentionally simple and fast — a
regex sweep, no network, no imports of the cited docs.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_THIS_FILE = Path(__file__).resolve()

# Files whose comments/docstrings we scan for citations. This guard file is
# excluded from its own scan — it legitimately quotes the (historically
# dangling) doc names it exists to forbid.
_SCANNED_FILES: list[Path] = [
    *sorted((_REPO_ROOT / "django_admin_react").rglob("*.py")),
    *(p for p in sorted((_REPO_ROOT / "tests").rglob("*.py")) if p.resolve() != _THIS_FILE),
    _REPO_ROOT / ".pre-commit-config.yaml",
]

# A cited Markdown doc, e.g. ``ARCHITECTURE.md`` or ``docs/ux/pwa.md``.
# Captures an optional path prefix so ``docs/foo.md`` resolves relative to
# the repo root, while a bare ``FOO.md`` may live anywhere in the tree.
_MD_REF_RE = re.compile(r"(?<![\w./-])((?:[\w./-]+/)?[A-Za-z0-9_-]+\.md)\b")

# A cited section, e.g. ``§4.5`` or ``§3``. The doc it belongs to is the
# nearest preceding ``*.md`` cite on the same line (the repo's convention
# is ``ARCHITECTURE.md §4.5``).
_SECTION_RE = re.compile(r"§\s*([\d]+(?:\.[\dA-Za-z]+)*)")


def _iter_lines() -> list[tuple[Path, int, str]]:
    out: list[tuple[Path, int, str]] = []
    for path in _SCANNED_FILES:
        if not path.is_file():
            continue
        for lineno, line in enumerate(path.read_text("utf-8").splitlines(), start=1):
            out.append((path, lineno, line))
    return out


def _resolve_md(ref: str) -> bool:
    """True if a cited ``*.md`` reference resolves to a real file."""
    # Path-qualified (``docs/ux/pwa.md``): resolve from the repo root.
    if "/" in ref:
        return (_REPO_ROOT / ref).is_file()
    # Bare filename (``ARCHITECTURE.md``): match anywhere in the tree,
    # skipping vendored / build dirs.
    skip = {"node_modules", ".git", "dist", ".venv", "__pycache__"}
    for candidate in _REPO_ROOT.rglob(ref):
        if not any(part in skip for part in candidate.parts):
            return True
    return False


def _section_exists(doc: Path, section: str) -> bool:
    """True if ``doc`` has a heading for ``§section`` (e.g. ``## 4.5``)."""
    text = doc.read_text("utf-8")
    # Headings look like ``## 4. Backend design`` or ``### 4.5 URL mounting``.
    pattern = re.compile(rf"^#{{1,6}}\s+{re.escape(section)}(?:[.\s]|$)", re.MULTILINE)
    return bool(pattern.search(text))


def test_no_dangling_md_references() -> None:
    """Every cited ``*.md`` file in the scanned sources exists."""
    failures: list[str] = []
    for path, lineno, line in _iter_lines():
        for match in _MD_REF_RE.finditer(line):
            ref = match.group(1)
            if not _resolve_md(ref):
                rel = path.relative_to(_REPO_ROOT)
                failures.append(f"{rel}:{lineno} cites missing doc {ref!r}")
    assert not failures, "Dangling Markdown references:\n" + "\n".join(failures)


def test_no_dangling_section_references() -> None:
    """Every ``§N`` cite resolves to a heading in the doc named on its line."""
    failures: list[str] = []
    for path, lineno, line in _iter_lines():
        sections = _SECTION_RE.findall(line)
        if not sections:
            continue
        md_refs = _MD_REF_RE.findall(line)
        if not md_refs:
            # A §N with no doc named on the same line — can't verify which
            # doc it belongs to, so we don't guess. The repo convention
            # always names the doc; flag the orphan so it gets fixed.
            rel = path.relative_to(_REPO_ROOT)
            cited = "/".join("§" + s for s in sections)
            failures.append(f"{rel}:{lineno} cites {cited} with no doc on the line")
            continue
        # The section belongs to the last doc named before it on the line.
        doc_ref = md_refs[-1]
        doc_path = _REPO_ROOT / doc_ref
        if not doc_path.is_file():
            # The missing-file case is already covered by the other test.
            continue
        for section in sections:
            if not _section_exists(doc_path, section):
                rel = path.relative_to(_REPO_ROOT)
                failures.append(f"{rel}:{lineno} cites {doc_ref} §{section} — no such heading")
    assert not failures, "Dangling section references:\n" + "\n".join(failures)
