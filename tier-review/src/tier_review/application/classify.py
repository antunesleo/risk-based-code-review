from __future__ import annotations

from tier_review.application.policy import ReviewPolicy
from tier_review.domain import ChangedFile, Decision, FileStatus, LineVerdict, Reason, Tier, Verdict
from tier_review.ports import CoverageIndex, DiffSource, ScopeResolver, TierCatalog


class ClassifyChange:
    """A change takes the most critical tier of any test that executes a changed line.

    Rules, in order:
      1. Ignored files (docs, ...) do not count.
      2. Test files changed -> unknown tier: they rewrite the map we rely on.
      3. Deleted, moved or non-Python files -> unknown tier: we cannot trace their impact.
      4. A changed line executed by tests -> most critical tier among those tests.
      5. A changed line not executed (new code, comments, signatures) -> inherits
         the tests of its enclosing function.
      6. Nothing found -> unknown tier: no test would catch a mistake there.
    """

    def __init__(
        self,
        diff: DiffSource,
        coverage: CoverageIndex,
        catalog: TierCatalog,
        scopes: ScopeResolver,
        policy: ReviewPolicy | None = None,
    ):
        self._diff = diff
        self._coverage = coverage
        self._catalog = catalog
        self._scopes = scopes
        self._policy = policy or ReviewPolicy()

    def execute(self) -> Decision:
        verdicts = tuple(v for changed in self._diff.changes() for v in self._classify_file(changed))
        tier = Tier.most_critical((v.verdict.tier for v in verdicts), default=self._policy.empty_change_tier)
        return Decision(tier=tier, verdicts=verdicts)

    def _classify_file(self, changed: ChangedFile) -> list[LineVerdict]:
        policy = self._policy
        if policy.is_ignored(changed.path):
            return []
        if policy.is_test(changed.path):
            return [self._file_level(changed, Reason.TEST_CHANGED)]
        if changed.status in (FileStatus.DELETED, FileStatus.RENAMED):
            return [self._file_level(changed, Reason.FILE_MOVED)]
        if not policy.is_source(changed.path):
            return [self._file_level(changed, Reason.UNANALYZABLE)]
        return [LineVerdict(changed.path, line, self._classify_line(changed.path, line)) for line in sorted(changed.lines)]

    def _classify_line(self, path: str, line: int) -> Verdict:
        tests = self._coverage.tests_for(path, [line])
        reason = Reason.DIRECT_COVERAGE
        if not tests:
            scope = self._scopes.enclosing_scope(path, line)
            tests = self._coverage.tests_for(path, scope) if scope else frozenset()
            reason = Reason.ENCLOSING_SCOPE
        if not tests:
            return Verdict(self._policy.unknown_tier, Reason.UNCOVERED)

        tiered = tuple(sorted(((t, self._catalog.tier_of(t)) for t in tests), key=_by_tier_then_name))
        if any(tier is None for _, tier in tiered):
            return Verdict(self._policy.unknown_tier, Reason.UNTIERED_TEST, tiered)
        return Verdict(Tier.most_critical(tier for _, tier in tiered), reason, tiered)

    def _file_level(self, changed: ChangedFile, reason: Reason) -> LineVerdict:
        return LineVerdict(changed.path, None, Verdict(self._policy.unknown_tier, reason))


def _by_tier_then_name(item: tuple[str, Tier | None]) -> tuple[int, str]:
    test_id, tier = item
    return (-1 if tier is None else int(tier), test_id)
