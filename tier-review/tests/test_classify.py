from tier_review.classify import CatalogTiers, ClassifyDiff
from tier_review.changes import ChangeBlock, ChangedFile, FileStatus
from tier_review.decision import Reason
from tier_review.tiers import Tier

from tests.fakes import FakeDiff, FakeLineTestCatalog, FakeScopes, FakeTestTierCatalog

TIERS = FakeTestTierCatalog({"t_billing": 0, "t_tickets": 1, "t_export": 2})
TEST_FILE_TIERS = FakeTestTierCatalog({"tests/test_billing.py::t_billing": 0, "tests/test_reports.py::t_export": 2})


def classify(*files, line_tests=None, scopes=None, test_tiers=TIERS, base=None):
    head = catalog_tiers(line_tests, test_tiers)
    return ClassifyDiff(FakeDiff(*files), head, FakeScopes(scopes), base=base).execute()


def catalog_tiers(line_tests=None, test_tiers=TIERS):
    return CatalogTiers(FakeLineTestCatalog(line_tests or {}), test_tiers)


def changed(path, *lines, status=FileStatus.MODIFIED, replaces=()):
    blocks = (ChangeBlock(frozenset(lines), frozenset(replaces)),) if replaces else ()
    return ChangedFile(path, status, frozenset(lines), blocks)


def test_line_takes_most_critical_tier_of_tests_that_execute_it():
    decision = classify(changed("app/sla.py", 10), line_tests={("app/sla.py", 10): {"t_export", "t_billing"}})

    assert decision.tier is Tier.CRITICAL
    assert decision.verdicts[0].verdict.tests == (("t_billing", Tier.CRITICAL), ("t_export", Tier.LOW))


def test_change_takes_most_critical_tier_across_files():
    decision = classify(
        changed("app/reports.py", 3),
        changed("app/tickets.py", 7),
        line_tests={("app/reports.py", 3): {"t_export"}, ("app/tickets.py", 7): {"t_tickets"}},
    )

    assert decision.tier is Tier.IMPORTANT


def test_unexecuted_line_inherits_tests_of_enclosing_function():
    decision = classify(
        changed("app/reports.py", 5),
        line_tests={("app/reports.py", 4): {"t_export"}},
        scopes={"app/reports.py": [range(3, 8)]},
    )

    assert decision.tier is Tier.LOW
    assert decision.verdicts[0].verdict.reason is Reason.ENCLOSING_SCOPE


def test_code_no_test_reaches_is_critical():
    decision = classify(changed("app/legacy.py", 2), scopes={"app/legacy.py": [range(1, 4)]})

    assert decision.tier is Tier.CRITICAL
    assert decision.verdicts[0].verdict.reason is Reason.UNCOVERED


def test_without_a_base_catalog_any_test_change_is_critical():
    decision = classify(changed("tests/test_reports.py", 9))

    assert decision.tier is Tier.CRITICAL
    assert decision.verdicts[0].verdict.reason is Reason.TEST_CHANGED


def test_test_code_takes_the_tier_of_the_tests_that_execute_it():
    decision = classify(
        changed("tests/test_reports.py", 9),
        line_tests={("tests/test_reports.py", 9): {"tests/test_reports.py::t_export"}},
        test_tiers=TEST_FILE_TIERS,
        base=catalog_tiers(test_tiers=TEST_FILE_TIERS),
    )

    assert decision.tier is Tier.LOW
    assert decision.verdicts[0].verdict.reason is Reason.DIRECT_COVERAGE


def test_fixture_takes_the_most_critical_tier_of_the_tests_using_it():
    decision = classify(
        changed("tests/conftest.py", 20),
        line_tests={("tests/conftest.py", 20): {"tests/test_reports.py::t_export", "tests/test_billing.py::t_billing"}},
        test_tiers=TEST_FILE_TIERS,
        base=catalog_tiers(test_tiers=TEST_FILE_TIERS),
    )

    assert decision.tier is Tier.CRITICAL


def test_test_module_code_takes_the_tests_it_defines():
    decision = classify(
        changed("tests/test_reports.py", 1),
        test_tiers=TEST_FILE_TIERS,
        base=catalog_tiers(test_tiers=TEST_FILE_TIERS),
    )

    assert decision.tier is Tier.LOW
    assert decision.verdicts[0].verdict.reason is Reason.TEST_MODULE


def test_conftest_module_code_takes_every_test_below_it():
    decision = classify(changed("tests/conftest.py", 1), test_tiers=TEST_FILE_TIERS, base=catalog_tiers(test_tiers=TEST_FILE_TIERS))

    assert decision.tier is Tier.CRITICAL
    assert decision.verdicts[0].verdict.reason is Reason.TEST_MODULE


def test_moving_a_test_to_a_less_critical_tier_keeps_its_base_tier():
    retagged = FakeTestTierCatalog({"tests/test_billing.py::t_billing": 2, "tests/test_reports.py::t_export": 2})
    decision = classify(
        changed("tests/test_billing.py", 5),
        line_tests={("tests/test_billing.py", 5): {"tests/test_billing.py::t_billing"}},
        test_tiers=retagged,
        base=catalog_tiers(test_tiers=TEST_FILE_TIERS),
    )

    assert decision.tier is Tier.CRITICAL
    assert decision.verdicts[-1].verdict.reason is Reason.TEST_DOWNGRADED


def test_removing_a_test_takes_its_base_tier():
    remaining = FakeTestTierCatalog({"tests/test_reports.py::t_export": 2})
    decision = classify(
        changed("tests/test_billing.py", 4, replaces=(4, 5, 6)),
        test_tiers=remaining,
        base=catalog_tiers(
            line_tests={("tests/test_billing.py", 5): {"tests/test_billing.py::t_billing"}},
            test_tiers=TEST_FILE_TIERS,
        ),
    )

    assert decision.tier is Tier.CRITICAL
    assert [v.verdict.reason for v in decision.verdicts] == [Reason.PREVIOUS_COVERAGE, Reason.TEST_REMOVED]


def test_replaced_code_keeps_the_tier_of_the_tests_that_used_to_run_it():
    decision = classify(
        changed("app/sla.py", 10, replaces=(10,)),
        line_tests={("app/sla.py", 10): {"t_export"}},
        base=catalog_tiers(line_tests={("app/sla.py", 10): {"t_billing", "t_export"}}),
    )

    assert decision.tier is Tier.CRITICAL
    assert decision.verdicts[0].verdict.reason is Reason.PREVIOUS_COVERAGE


def test_test_without_tier_is_treated_as_critical():
    decision = classify(changed("app/x.py", 1), line_tests={("app/x.py", 1): {"t_new"}})

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
