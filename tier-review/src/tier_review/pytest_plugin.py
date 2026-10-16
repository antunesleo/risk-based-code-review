"""pytest plugin: reads `@pytest.mark.tier(N)` and writes the test -> tier catalog.

    pytest --tier-catalog=test-tiers.json --tier-strict

Node ids match the contexts pytest-cov records with `--cov-context=test`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tier_review.catalog import JsonTierCatalog
from tier_review.tiers import Tier


def pytest_addoption(parser):
    group = parser.getgroup("tier-review")
    group.addoption("--tier-catalog", metavar="PATH", help="write the test -> tier catalog to PATH")
    group.addoption("--tier-strict", action="store_true", help="fail the run if any test has no tier marker")


def pytest_configure(config):
    config.addinivalue_line("markers", "tier(level): error-impact tier of the flow this test protects (0, 1 or 2)")


def pytest_collection_modifyitems(session, config, items):
    tiers, problems = {}, []
    for item in items:
        marker = item.get_closest_marker("tier")
        if marker is None:
            problems.append(f"{item.nodeid}: missing @pytest.mark.tier")
            continue
        try:
            tiers[item.nodeid] = Tier.parse(marker.args[0] if marker.args else None)
        except ValueError as error:
            problems.append(f"{item.nodeid}: {error}")

    if problems and config.getoption("tier_strict"):
        raise pytest.UsageError("tier-review:\n  " + "\n  ".join(problems))
    if path := config.getoption("tier_catalog"):
        JsonTierCatalog(tiers).dump(Path(path))
