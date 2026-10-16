from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from tier_review.domain.tier import Tier


class Reason(Enum):
    DIRECT_COVERAGE = "executed by tests"
    ENCLOSING_SCOPE = "not executed itself; inherits tests of the enclosing function"
    UNCOVERED = "no test executes this code, nothing would catch a mistake"
    UNTIERED_TEST = "executed by a test that has no tier"
    TEST_CHANGED = "test code changed, which rewrites the coverage map itself"
    FILE_MOVED = "file deleted or moved, its importers cannot be traced from this change"
    UNANALYZABLE = "not Python source, impact cannot be traced"


@dataclass(frozen=True)
class Verdict:
    tier: Tier
    reason: Reason
    tests: tuple[tuple[str, Tier | None], ...] = ()


@dataclass(frozen=True)
class LineVerdict:
    path: str
    line: int | None  # None for file-level verdicts
    verdict: Verdict


@dataclass(frozen=True)
class Decision:
    tier: Tier
    verdicts: tuple[LineVerdict, ...]

    @property
    def review_route(self) -> str:
        return self.tier.review_route

    @property
    def decisive(self) -> tuple[LineVerdict, ...]:
        """The verdicts that pushed the change into its tier."""
        return tuple(v for v in self.verdicts if v.verdict.tier == self.tier)
