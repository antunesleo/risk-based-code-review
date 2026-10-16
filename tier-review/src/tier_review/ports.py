"""Interfaces the application depends on. Adapters implement them."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from tier_review.domain import ChangeSet, Tier


class DiffSource(Protocol):
    def changes(self) -> ChangeSet:
        """Files and new-side line numbers touched by the change, relative to the project root."""


class CoverageIndex(Protocol):
    def tests_for(self, path: str, lines: Iterable[int]) -> frozenset[str]:
        """Ids of the tests that executed any of `lines` in `path`."""


class TierCatalog(Protocol):
    def tier_of(self, test_id: str) -> Tier | None:
        """Tier assigned to a test, or None if the test is unknown or untagged."""


class ScopeResolver(Protocol):
    def enclosing_scope(self, path: str, line: int) -> range | None:
        """Lines of the innermost function containing `line`, or None at module level."""
