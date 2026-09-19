"""Release changelog helpers (scripts/changelog.py)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_CHANGELOG_PY = _REPO / "scripts" / "changelog.py"

_HEADER = """# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]
"""


def _run(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_CHANGELOG_PY), "--repo", str(repo), *args],
        check=check,
        capture_output=True,
        text=True,
    )


def test_check_unreleased_fails_when_empty(tmp_path: Path) -> None:
    (tmp_path / "CHANGELOG.md").write_text(_HEADER + "\n", encoding="utf-8")
    result = _run(tmp_path, "check-unreleased", check=False)
    assert result.returncode != 0
    assert "empty" in result.stderr


def test_cut_moves_unreleased_and_notes_print_section(tmp_path: Path) -> None:
    (tmp_path / "CHANGELOG.md").write_text(
        _HEADER + "\n### Added\n- First feature.\n\n## [0.0.1] - 2026-01-01\n\n### Added\n- Older.\n",
        encoding="utf-8",
    )
    _run(tmp_path, "check-unreleased")
    _run(tmp_path, "cut", "0.1.0", "--date", "2026-09-19")
    text = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [Unreleased]" in text
    assert "## [0.1.0] - 2026-09-19" in text
    assert "First feature." in text
    unreleased, _, rest = text.partition("## [0.1.0] - 2026-09-19")
    assert "First feature." not in unreleased
    assert "First feature." in rest
    notes = _run(tmp_path, "notes", "0.1.0")
    assert "First feature." in notes.stdout
    assert "Older." not in notes.stdout


def test_cut_refuses_duplicate_version(tmp_path: Path) -> None:
    (tmp_path / "CHANGELOG.md").write_text(
        _HEADER + "\n### Added\n- New.\n\n## [0.1.0] - 2026-01-01\n\n### Added\n- Old.\n",
        encoding="utf-8",
    )
    result = _run(tmp_path, "cut", "0.1.0", "--date", "2026-09-19", check=False)
    assert result.returncode != 0
