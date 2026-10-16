from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from tier_review.tiers import Tier


class Reason(Enum):
    DIRECT_COVERAGE = "executed by tests"
    ENCLOSING_SCOPE = "not executed itself; inherits tests of the enclosing function"
    PREVIOUS_COVERAGE = "the code it replaces or removes was executed by tests on the base"
    TEST_MODULE = "test module code, shared by every test it defines or configures"
    UNCOVERED = "no test executes this code, nothing would catch a mistake"
    UNTIERED_TEST = "executed by a test that has no tier"
    TEST_DOWNGRADED = "test moved to a less critical tier, which lowers the tier of the code it protects"
    TEST_REMOVED = "test removed, the flow it protected loses its safety net"
    TEST_CHANGED = "test code changed and there is no base map to compare against"
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
