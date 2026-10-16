"""LineTestCatalog backed by a coverage.py data file recorded with per-test contexts.

Record it with pytest-cov: `pytest --cov --cov-context=test`, which labels every
executed line with `<test node id>|setup|run|teardown`.
"""
from __future__ import annotations

from collections.abc import Iterable
from functools import cache
from pathlib import Path

from coverage import CoverageData


class CoveragePyLineTestCatalog:
    def __init__(self, data_file: Path):
        if not data_file.exists():
            raise FileNotFoundError(f"coverage data not found: {data_file}")
        self._data = CoverageData(basename=str(data_file))
        self._data.read()
        if not self._data.measured_contexts() - {""}:
            raise ValueError(f"{data_file} has no per-test contexts; record it with --cov-context=test")
        self._measured = {Path(f).as_posix(): f for f in self._data.measured_files()}

    def tests_for(self, path: str, lines: Iterable[int]) -> frozenset[str]:
        by_line = self._contexts_by_line(path)
        return frozenset(test for line in lines for test in by_line.get(line, ()))

    @cache
    def _contexts_by_line(self, path: str) -> dict[int, frozenset[str]]:
        measured = self._resolve(path)
        if measured is None:
            return {}
        return {
            line: frozenset(_test_id(context) for context in contexts if context)
            for line, contexts in self._data.contexts_by_lineno(measured).items()
        }

    def _resolve(self, path: str) -> str | None:
        """Exact match for `relative_files = True` data, suffix match for absolute paths."""
        if path in self._measured:
            return self._measured[path]
        candidates = [original for posix, original in self._measured.items() if posix.endswith("/" + path)]
        return candidates[0] if len(candidates) == 1 else None


def _test_id(context: str) -> str:
    return context.rsplit("|", 1)[0] if context.endswith(("|setup", "|run", "|teardown")) else context
