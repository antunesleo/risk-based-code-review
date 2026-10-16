"""Render a Decision for humans (text) or machines (json)."""
from __future__ import annotations

import json
from itertools import groupby

from tier_review.decision import Decision, LineVerdict
from tier_review.tiers import Tier


def render_json(decision: Decision) -> str:
    return json.dumps(
        {
            "tier": int(decision.tier),
            "review": decision.review_route,
            "changes": [
                {
                    "path": path,
                    "lines": _span(lines),
                    "tier": int(verdict.tier),
                    "reason": verdict.reason.name,
                    "tests": [{"id": t, "tier": None if tier is None else int(tier)} for t, tier in verdict.tests],
                }
                for path, lines, verdict in _ranges(decision.verdicts)
            ],
        },
        indent=2,
    )


def render_text(decision: Decision, max_tests: int = 5) -> str:
    out = [f"REVIEW TIER {int(decision.tier)} ({decision.tier.name}): {decision.review_route}", ""]
    if not decision.verdicts:
        out.append("No relevant changes found.")
        return "\n".join(out)

    out.append("Why:")
    for path, lines, verdict in _ranges(decision.decisive):
        out.append(f"  {_location(path, lines)}  {verdict.reason.value}")
        shown = verdict.tests[:max_tests]
        out += [f"      {_tier_label(tier)}  {test}" for test, tier in shown]
        if len(verdict.tests) > len(shown):
            out.append(f"      ... and {len(verdict.tests) - len(shown)} more")

    out += ["", "All changed code:"]
    for path, lines, verdict in _ranges(decision.verdicts):
        out.append(f"  {_tier_label(verdict.tier)}  {_location(path, lines):<32} {verdict.reason.name.lower()}")
    return "\n".join(out)


def _ranges(verdicts: tuple[LineVerdict, ...]):
    """Collapse consecutive lines of a file that share the same verdict."""
    for (path, verdict), group in groupby(verdicts, key=lambda v: (v.path, v.verdict)):
        lines = [v.line for v in group]
        if lines == [None]:
            yield path, None, verdict
            continue
        for block in _consecutive(lines):
            yield path, block, verdict


def _consecutive(lines: list[int]):
    block = [lines[0]]
    for line in lines[1:]:
        if line == block[-1] + 1:
            block.append(line)
        else:
            yield block
            block = [line]
    yield block


def _span(lines: list[int] | None) -> list[int] | None:
    return None if lines is None else [lines[0], lines[-1]]


def _location(path: str, lines: list[int] | None) -> str:
    if lines is None:
        return path
    return f"{path}:{lines[0]}" if len(lines) == 1 else f"{path}:{lines[0]}-{lines[-1]}"


def _tier_label(tier: Tier | None) -> str:
    return "tier ?" if tier is None else f"tier {int(tier)}"


