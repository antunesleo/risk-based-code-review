import subprocess
import sys
import textwrap

from tier_review import catalog
from tier_review.catalog import catalog_tiers, snapshot
from tier_review.cli import main
from tier_review.line_test_catalog import CoveragePyLineTestCatalog
from tier_review.test_tier_catalog import JsonTestTierCatalog
from tier_review.tiers import Tier

APP = """\
def charge(amount):
    return amount * 2
"""

TEST = """\
import pytest

from app import charge


@pytest.mark.tier(0)
def test_charge():
    assert charge(2) == {expected}
"""

COVERAGERC = """\
[run]
source = .
relative_files = True
"""


def make_project(root, expected=4):
    root.mkdir(parents=True, exist_ok=True)
    (root / "app.py").write_text(APP)
    (root / "test_app.py").write_text(TEST.format(expected=expected))
    (root / ".coveragerc").write_text(COVERAGERC)
    (root / "pytest.ini").write_text("[pytest]\naddopts = -p no:cacheprovider\n")
    return root


def git(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=repo, check=True, capture_output=True)


def test_catalog_records_both_catalogs(tmp_path):
    project = make_project(tmp_path / "project")
    out = tmp_path / "catalog"

    assert catalog_tiers(project, out) == 0

    line_tests = CoveragePyLineTestCatalog(catalog.line_tests_path(out))
    test_tiers = JsonTestTierCatalog.load(catalog.test_tiers_path(out))
    assert line_tests.tests_for("app.py", [2]) == {"test_app.py::test_charge"}
    assert test_tiers.tier_of("test_app.py::test_charge") is Tier.CRITICAL


def test_failing_tests_still_leave_a_catalog(tmp_path, capsys):
    project = make_project(tmp_path / "project", expected=5)
    out = tmp_path / "catalog"

    assert catalog_tiers(project, out) == 0

    assert "some tests failed" in capsys.readouterr().err
    assert CoveragePyLineTestCatalog(catalog.line_tests_path(out)).tests_for("app.py", [2]) == {"test_app.py::test_charge"}


def test_other_pytest_errors_are_returned(tmp_path):
    project = make_project(tmp_path / "project")
    (project / "test_app.py").write_text("def test_untiered():\n    pass\n")

    assert catalog_tiers(project, tmp_path / "catalog") == 4  # usage error: missing tier marker


def test_catalog_runs_the_suite_with_tier_review_flags(tmp_path):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0)

    catalog_tiers(tmp_path, tmp_path / "out", pytest_args=["-k", "billing"], run=run)

    command, kwargs = calls[0]
    assert command[:3] == [sys.executable, "-m", "pytest"]
    assert "--cov-context=test" in command and "--tier-strict" in command
    assert f"--test-tiers={tmp_path / 'out' / 'test-tiers.json'}" in command
    assert command[-2:] == ["-k", "billing"]
    assert kwargs["cwd"] == tmp_path
    assert kwargs["env"]["COVERAGE_FILE"] == str(tmp_path / "out" / ".coverage")


def test_snapshot_extracts_only_the_project_at_the_ref(tmp_path):
    repo = tmp_path / "repo"
    project = make_project(repo / "service")
    (repo / "other.txt").write_text("not part of the project\n")
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    (project / "app.py").write_text("changed\n")

    dest = snapshot(project, "HEAD", tmp_path / "snap")

    assert (dest / "app.py").read_text() == APP
    assert not (dest / "other.txt").exists()


def test_cli_catalogs_a_ref_and_classifies_against_it(tmp_path, capsys):
    repo = tmp_path / "repo"
    project = make_project(repo / "service")
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    (project / "app.py").write_text(APP.replace("* 2", "* 3"))
    (project / "test_app.py").write_text(TEST.format(expected=6))

    assert main(["catalog", "--project", str(project), "--out", str(tmp_path / "head")]) == 0
    assert main(["catalog", "--project", str(project), "--out", str(tmp_path / "base"), "--ref", "HEAD"]) == 0
    code = main([
        "classify", "--repo", str(repo), "--project", "service", "--format", "json",
        "--catalog", str(tmp_path / "head"), "--base-catalog", str(tmp_path / "base"),
    ])

    assert code == 0
    assert '"tier": 0' in capsys.readouterr().out
