"""Command line: reads the diff and the catalogs, prints the decision."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tier_review.line_test_catalog import CoveragePyLineTestCatalog
from tier_review.diff import GitDiffSource, ProjectScope, TextDiffSource
from tier_review.scopes import AstScopeResolver
from tier_review.test_tier_catalog import JsonTestTierCatalog
from tier_review.classify import CatalogTiers, ClassifyDiff
from tier_review.report import render_json, render_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tier-review", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    classify = sub.add_parser("classify", help="decide the review tier of a change")
    classify.add_argument("--repo", type=Path, default=Path("."), help="git repository root (default: .)")
    classify.add_argument("--project", default="", help="project directory inside the repo, e.g. example-codebase")
    classify.add_argument("--base", default="HEAD", help="git ref to diff the working tree against (default: HEAD)")
    classify.add_argument("--diff-file", help="read a unified diff from this file ('-' for stdin) instead of git")
    classify.add_argument("--line-tests", type=Path, required=True, help="line -> tests: coverage.py data file with test contexts")
    classify.add_argument("--test-tiers", type=Path, required=True, help="test -> tier: JSON written by the pytest plugin")
    classify.add_argument("--base-line-tests", type=Path, help="line -> tests recorded on --base (enables test-aware rules)")
    classify.add_argument("--base-test-tiers", type=Path, help="test -> tier recorded on --base")
    classify.add_argument("--format", choices=("text", "json"), default="text")
    classify.add_argument("--max-tests", type=int, default=5, help="tests listed per finding in text output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
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

    if (args.base_line_tests is None) != (args.base_test_tiers is None):
        raise ValueError("--base-line-tests and --base-test-tiers go together")
    base = None
    if args.base_line_tests:
        base = _catalog_tiers(args.base_line_tests, args.base_test_tiers)

    use_case = ClassifyDiff(
        diff=diff,
        head=_catalog_tiers(args.line_tests, args.test_tiers),
        scopes=AstScopeResolver(args.repo / args.project),
        base=base,
    )
    return use_case.execute()


def _catalog_tiers(line_tests: Path, test_tiers: Path) -> CatalogTiers:
    return CatalogTiers(CoveragePyLineTestCatalog(line_tests), JsonTestTierCatalog.load(test_tiers))


if __name__ == "__main__":
    sys.exit(main())
