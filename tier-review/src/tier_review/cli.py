"""Composition root: wires adapters into the use case and prints the decision."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tier_review.adapters.coverage_index import CoveragePyIndex
from tier_review.adapters.diff import GitDiffSource, ProjectScope, TextDiffSource
from tier_review.adapters.python_scopes import AstScopeResolver
from tier_review.adapters.tier_catalog import JsonTierCatalog
from tier_review.application import ClassifyChange
from tier_review.reporting import render_json, render_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tier-review", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    classify = sub.add_parser("classify", help="decide the review tier of a change")
    classify.add_argument("--repo", type=Path, default=Path("."), help="git repository root (default: .)")
    classify.add_argument("--project", default="", help="project directory inside the repo, e.g. helpdesk")
    classify.add_argument("--base", default="HEAD", help="git ref to diff the working tree against (default: HEAD)")
    classify.add_argument("--diff-file", help="read a unified diff from this file ('-' for stdin) instead of git")
    classify.add_argument("--coverage", type=Path, required=True, help="coverage.py data file with test contexts")
    classify.add_argument("--catalog", type=Path, required=True, help="test -> tier JSON written by the pytest plugin")
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

    use_case = ClassifyChange(
        diff=diff,
        coverage=CoveragePyIndex(args.coverage),
        catalog=JsonTierCatalog.load(args.catalog),
        scopes=AstScopeResolver(args.repo / args.project),
    )
    return use_case.execute()


if __name__ == "__main__":
    sys.exit(main())
