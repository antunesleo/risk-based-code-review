"""Catalog tiers: run a project's test suite and record its two catalogs into one directory.

    <out>/.coverage         line -> tests (LineTestCatalog, pytest-cov with test contexts)
    <out>/test-tiers.json   test -> tier  (TestTierCatalog, the tier-review pytest plugin)

With a git ref, the project is cataloged as it was at that ref: its tree is extracted to a
temporary directory and the suite runs there, with the current environment's dependencies.
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path

LINE_TESTS_FILE = ".coverage"
TEST_TIERS_FILE = "test-tiers.json"

# pytest exit codes: 0 all passed, 1 some tests failed. Anything else (interrupted,
# internal error, usage error such as a missing tier marker, no tests) is a real error.
TESTS_FAILED = 1

Runner = Callable[..., subprocess.CompletedProcess]


def line_tests_path(catalog_dir: Path) -> Path:
    return catalog_dir / LINE_TESTS_FILE


def test_tiers_path(catalog_dir: Path) -> Path:
    return catalog_dir / TEST_TIERS_FILE


def catalog_tiers(
    project: Path,
    out: Path,
    ref: str | None = None,
    pytest_args: Sequence[str] = (),
    run: Runner = subprocess.run,
) -> int:
    """Catalog `project` (at `ref`, or as it is on disk) into `out`. Returns an exit code.

    Failing tests still leave a usable catalog: each test keeps the lines it reached
    before failing. So they only produce a warning.
    """
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for stale in (line_tests_path(out), test_tiers_path(out)):
        stale.unlink(missing_ok=True)

    if ref is None:
        code = _run_suite(project, out, pytest_args, run)
    else:
        with tempfile.TemporaryDirectory(prefix="tier-review-") as tmp:
            code = _run_suite(snapshot(project, ref, Path(tmp)), out, pytest_args, run)

    if code == TESTS_FAILED:
        print("tier-review: some tests failed; their lines are cataloged up to the failure", file=sys.stderr)
        return 0
    return code


def snapshot(project: Path, ref: str, dest: Path) -> Path:
    """Extract `project` as it was at `ref` into `dest`. Returns the extracted project dir."""
    # Run inside the project directory, git archive exports only that subtree,
    # with paths relative to it.
    result = subprocess.run(
        ["git", "archive", "--format=tar", ref], cwd=project, capture_output=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"git archive {ref} failed: {result.stderr.decode().strip()}")
    with tarfile.open(fileobj=io.BytesIO(result.stdout)) as archive:
        archive.extractall(dest, filter="data")
    return dest


def _run_suite(project: Path, out: Path, pytest_args: Sequence[str], run: Runner) -> int:
    command = [
        sys.executable, "-m", "pytest", "-q",
        "--cov", "--cov-context=test", "--cov-report=",
        f"--test-tiers={test_tiers_path(out)}", "--tier-strict",
        *pytest_args,
    ]
    env = {**os.environ, "COVERAGE_FILE": str(line_tests_path(out))}
    return run(command, cwd=project, env=env, check=False).returncode
