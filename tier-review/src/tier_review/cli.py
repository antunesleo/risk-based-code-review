"""Command line: catalogs tiers, or reads the diff and the catalogs and prints the decision."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from tier_review import catalog
from tier_review.line_test_catalog import CoveragePyLineTestCatalog
from tier_review.diff import GitDiffSource, ProjectScope, TextDiffSource
from tier_review.scopes import AstScopeResolver
from tier_review.test_tier_catalog import JsonTestTierCatalog
from tier_review.classify import CatalogTiers, ClassifyDiff
from tier_review.report import render_json, render_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tier-review", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    project = os.environ.get("TIER_REVIEW_PROJECT", "")

    cat = sub.add_parser(
        "catalog",
        help="run the test suite and record line -> tests and test -> tier",
        description="Arguments after -- go to pytest.",
    )
    cat.add_argument("--project", type=Path, default=Path(project or "."),
                     help="project directory, where pytest runs (default: $TIER_REVIEW_PROJECT or .)")
    cat.add_argument("--out", type=Path, required=True, help=f"directory to write {catalog.LINE_TESTS_FILE} and {catalog.TEST_TIERS_FILE} to")
    cat.add_argument("--ref", help="catalog the project as it was at this git ref, e.g. the diff base")

    classify = sub.add_parser("classify", help="decide the review tier of a change")
    classify.add_argument("--repo", type=Path, default=Path("."), help="git repository root (default: .)")
    classify.add_argument("--project", default=project,
                          help="project directory inside the repo, e.g. example-codebase (default: $TIER_REVIEW_PROJECT)")
    classify.add_argument("--base", default="HEAD", help="git ref to diff the working tree against (default: HEAD)")
    classify.add_argument("--diff-file", help="read a unified diff from this file ('-' for stdin) instead of git")
    classify.add_argument("--catalog", type=Path, help="catalog directory of the working tree (written by `catalog`)")
    classify.add_argument("--base-catalog", type=Path, help="catalog directory of --base (enables test-aware rules)")
    classify.add_argument("--line-tests", type=Path, help="instead of --catalog: coverage.py data file with test contexts")
    classify.add_argument("--test-tiers", type=Path, help="instead of --catalog: JSON written by the pytest plugin")
    classify.add_argument("--base-line-tests", type=Path, help="instead of --base-catalog: line -> tests on --base")
    classify.add_argument("--base-test-tiers", type=Path, help="instead of --base-catalog: test -> tier on --base")
    classify.add_argument("--format", choices=("text", "json"), default="text")
    classify.add_argument("--max-tests", type=int, default=5, help="tests listed per finding in text output")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    pytest_args: list[str] = []
    if "--" in argv:
        at = argv.index("--")
        argv, pytest_args = argv[:at], argv[at + 1:]
    args = build_parser().parse_args(argv)
    try:
        if args.command == "catalog":
            return catalog.catalog_tiers(args.project, args.out, args.ref, pytest_args)
        decision = _classify(args)
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        print(f"tier-review: {error}", file=sys.stderr)
        return 2
    print(render_json(decision) if args.format == "json" else render_text(decision, args.max_tests))
    return 0


def _classify(args: argparse.Namespace):
    scope = ProjectScope(args.project)
    if args.diff_file:
        text = sys.stdin.read() if args.diff_file == "-" else Path(args.diff_file).read_text()
        diff = TextDiffSource(text, scope)
    else:
        diff = GitDiffSource(args.repo, args.base, scope)

    head = _catalog_tiers(args.catalog, args.line_tests, args.test_tiers, "")
    if head is None:
        raise ValueError("give --catalog, or --line-tests and --test-tiers")
    base = _catalog_tiers(args.base_catalog, args.base_line_tests, args.base_test_tiers, "base-")

    use_case = ClassifyDiff(
        diff=diff,
        head=head,
        scopes=AstScopeResolver(args.repo / args.project),
        base=base,
    )
    return use_case.execute()


def _catalog_tiers(directory: Path | None, line_tests: Path | None, test_tiers: Path | None, flag: str) -> CatalogTiers | None:
    """A catalog directory, or its two files given one by one (each file flag overrides the directory)."""
    if directory is not None:
        line_tests = line_tests or catalog.line_tests_path(directory)
        test_tiers = test_tiers or catalog.test_tiers_path(directory)
    if line_tests is None and test_tiers is None:
        return None
    if line_tests is None or test_tiers is None:
        raise ValueError(f"--{flag}line-tests and --{flag}test-tiers go together")
    return CatalogTiers(CoveragePyLineTestCatalog(line_tests), JsonTestTierCatalog.load(test_tiers))


if __name__ == "__main__":
    sys.exit(main())
