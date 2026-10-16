from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from tier_review.changes import ChangedFile, ChangeSet, FileStatus
from tier_review.decision import Decision, LineVerdict, Reason, Verdict
from tier_review.policy import ReviewPolicy
from tier_review.tiers import Tier

# What the classifier reads. diff.py, coverage_index.py, catalog.py and scopes.py
# implement these; tests use in-memory fakes.


class DiffSource(Protocol):
    def changes(self) -> ChangeSet:
        """Files and new-side line numbers touched by the change, relative to the project root."""


class LineTestCatalog(Protocol):
    def tests_for(self, path: str, lines: Iterable[int]) -> frozenset[str]:
        """Ids of the tests that executed any of `lines` in `path`."""


class TestTierCatalog(Protocol):
    def tier_of(self, test_id: str) -> Tier | None:
        """Tier assigned to a test, or None if the test is unknown or untagged."""

    def test_ids(self) -> frozenset[str]:
        """Every test the catalog knows."""


class ScopeResolver(Protocol):
    def enclosing_scope(self, path: str, line: int) -> range | None:
        """Lines of the innermost function containing `line`, or None at module level."""


@dataclass(frozen=True)
class CatalogTiers:
    """What the catalog step records for one commit: line -> tests and test -> tier."""

    line_tests: LineTestCatalog
    test_tiers: TestTierCatalog


class ClassifyDiff:
    """A diff takes the most critical tier of any test that executes a changed line.

    Test code is classified like application code: a test line takes the tier of the
    tests that execute it (the test itself, or every test using a fixture). Comparing
    with the base catalog closes the ways a diff could make code look safer than it is.

    Rules, in order:
      1. Ignored files (docs, ...) do not count.
      2. Without a base catalog, a changed test file -> unknown tier: we cannot tell an
         edit from a downgrade of the catalog we rely on.
      3. Deleted or moved application files, non-Python files -> unknown tier: we
         cannot trace their impact.
      4. A changed line takes the most critical tier among
         - the tests that execute it, or else the tests of its enclosing function, and
         - the tests that executed the base lines it replaces or removes.
         A test's tier is the most critical of its base and new tier.
      5. Test module code no test executes (imports, constants) -> tests it defines,
         or for a conftest.py every test below it.
      6. Nothing found -> unknown tier: no test would catch a mistake there.
      7. A test removed or moved to a less critical tier -> its base tier.
    """

    def __init__(
        self,
        diff: DiffSource,
        head: CatalogTiers,
        scopes: ScopeResolver,
        policy: ReviewPolicy | None = None,
        base: CatalogTiers | None = None,
    ):
        self._diff = diff
        self._head = head
        self._scopes = scopes
        self._policy = policy or ReviewPolicy()
        self._base = base

    def execute(self) -> Decision:
        verdicts = tuple(v for changed in self._diff.changes() for v in self._classify_file(changed))
        verdicts += self._weakened_tests()
        tier = Tier.most_critical((v.verdict.tier for v in verdicts), default=self._policy.empty_change_tier)
        return Decision(tier=tier, verdicts=verdicts)

    def _classify_file(self, changed: ChangedFile) -> list[LineVerdict]:
        policy = self._policy
        if policy.is_ignored(changed.path):
            return []
        is_test = policy.is_test(changed.path)
        if is_test and self._base is None:
            return [self._file_level(changed, Reason.TEST_CHANGED)]
        if is_test and changed.status is FileStatus.DELETED:
            return []  # its tests are reported as removed
        if not is_test and changed.status in (FileStatus.DELETED, FileStatus.RENAMED):
            return [self._file_level(changed, Reason.FILE_MOVED)]
        if not policy.is_source(changed.path):
            return [self._file_level(changed, Reason.UNANALYZABLE)]
        return [LineVerdict(changed.path, line, self._classify_line(changed, line, is_test)) for line in sorted(changed.lines)]

    def _classify_line(self, changed: ChangedFile, line: int, is_test: bool) -> Verdict:
        path = changed.path
        current = self._head.line_tests.tests_for(path, [line])
        reason = Reason.DIRECT_COVERAGE
        if not current:
            scope = self._scopes.enclosing_scope(path, line)
            current = self._head.line_tests.tests_for(path, scope) if scope else frozenset()
            reason = Reason.ENCLOSING_SCOPE
        previous = self._base.line_tests.tests_for(path, changed.replaced_lines(line)) if self._base else frozenset()

        tests = current | previous
        if not tests and is_test:
            tests, reason = self._tests_defined_by(path), Reason.TEST_MODULE
        if not tests:
            return Verdict(self._policy.unknown_tier, Reason.UNCOVERED)

        tiered = tuple(sorted(((t, self._tier_of(t)) for t in tests), key=_by_tier_then_name))
        if any(tier is None for _, tier in tiered):
            return Verdict(self._policy.unknown_tier, Reason.UNTIERED_TEST, tiered)
        tier = Tier.most_critical(tier for _, tier in tiered)
        if reason is not Reason.TEST_MODULE and tier not in {self._tier_of(t) for t in current}:
            reason = Reason.PREVIOUS_COVERAGE
        return Verdict(tier, reason, tiered)

    def _weakened_tests(self) -> tuple[LineVerdict, ...]:
        """Tests the change removes or moves to a less critical tier."""
        if self._base is None:
            return ()
        current = self._head.test_tiers.test_ids()
        verdicts = []
        for test in sorted(self._base.test_tiers.test_ids()):
            was = self._base.test_tiers.tier_of(test)
            now = self._head.test_tiers.tier_of(test)
            if was is None:
                continue
            if test not in current:
                reason = Reason.TEST_REMOVED
            elif now is not None and now > was:
                reason = Reason.TEST_DOWNGRADED
            else:
                continue
            verdicts.append(LineVerdict(_test_path(test), None, Verdict(was, reason, ((test, was),))))
        return tuple(verdicts)

    def _tier_of(self, test: str) -> Tier | None:
        catalogs = [self._head.test_tiers] + ([self._base.test_tiers] if self._base else [])
        tiers = [tier for catalog in catalogs if (tier := catalog.tier_of(test)) is not None]
        return Tier.most_critical(tiers) if tiers else None

    def _tests_defined_by(self, path: str) -> frozenset[str]:
        """Tests a test module defines, or every test below a conftest.py."""
        known = self._head.test_tiers.test_ids() | (self._base.test_tiers.test_ids() if self._base else frozenset())
        directory, _, name = path.rpartition("/")
        if name == "conftest.py":
            return frozenset(t for t in known if not directory or _test_path(t).startswith(directory + "/"))
        return frozenset(t for t in known if _test_path(t) == path)

    def _file_level(self, changed: ChangedFile, reason: Reason) -> LineVerdict:
        return LineVerdict(changed.path, None, Verdict(self._policy.unknown_tier, reason))


def _test_path(test_id: str) -> str:
    return test_id.split("::", 1)[0]


def _by_tier_then_name(item: tuple[str, Tier | None]) -> tuple[int, str]:
    test_id, tier = item
    return (-1 if tier is None else int(tier), test_id)
