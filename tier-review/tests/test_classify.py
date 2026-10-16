from tier_review.application import ClassifyChange
from tier_review.domain import ChangedFile, FileStatus, Reason, Tier

from tests.fakes import FakeCatalog, FakeCoverage, FakeDiff, FakeScopes

CATALOG = FakeCatalog({"t_billing": 0, "t_tickets": 1, "t_export": 2})


def classify(*files, coverage=None, scopes=None, catalog=CATALOG):
    return ClassifyChange(FakeDiff(*files), FakeCoverage(coverage or {}), catalog, FakeScopes(scopes)).execute()


def changed(path, *lines, status=FileStatus.MODIFIED):
    return ChangedFile(path, status, frozenset(lines))


def test_line_takes_most_critical_tier_of_tests_that_execute_it():
    decision = classify(changed("app/sla.py", 10), coverage={("app/sla.py", 10): {"t_export", "t_billing"}})

    assert decision.tier is Tier.CRITICAL
    assert decision.verdicts[0].verdict.tests == (("t_billing", Tier.CRITICAL), ("t_export", Tier.LOW))


def test_change_takes_most_critical_tier_across_files():
    decision = classify(
        changed("app/reports.py", 3),
        changed("app/tickets.py", 7),
        coverage={("app/reports.py", 3): {"t_export"}, ("app/tickets.py", 7): {"t_tickets"}},
    )

    assert decision.tier is Tier.IMPORTANT


def test_unexecuted_line_inherits_tests_of_enclosing_function():
    decision = classify(
        changed("app/reports.py", 5),
        coverage={("app/reports.py", 4): {"t_export"}},
        scopes={"app/reports.py": [range(3, 8)]},
    )

    assert decision.tier is Tier.LOW
    assert decision.verdicts[0].verdict.reason is Reason.ENCLOSING_SCOPE


def test_code_no_test_reaches_is_critical():
    decision = classify(changed("app/legacy.py", 2), scopes={"app/legacy.py": [range(1, 4)]})

    assert decision.tier is Tier.CRITICAL
    assert decision.verdicts[0].verdict.reason is Reason.UNCOVERED


def test_changing_a_test_is_critical_even_if_it_is_a_low_tier_test():
    decision = classify(changed("tests/test_reports.py", 9))

    assert decision.tier is Tier.CRITICAL
    assert decision.verdicts[0].verdict.reason is Reason.TEST_CHANGED


def test_test_without_tier_is_treated_as_critical():
    decision = classify(changed("app/x.py", 1), coverage={("app/x.py", 1): {"t_new"}})

    assert decision.verdicts[0].verdict.reason is Reason.UNTIERED_TEST
    assert decision.tier is Tier.CRITICAL


def test_deleted_moved_and_non_python_files_are_critical():
    decision = classify(
        changed("app/old.py", status=FileStatus.DELETED),
        changed("requirements.txt", 3),
    )

    assert [v.verdict.reason for v in decision.verdicts] == [Reason.FILE_MOVED, Reason.UNANALYZABLE]
    assert decision.tier is Tier.CRITICAL


def test_docs_only_change_is_low_tier():
    decision = classify(changed("README.md", 1, 2))

    assert decision.verdicts == ()
    assert decision.tier is Tier.LOW
