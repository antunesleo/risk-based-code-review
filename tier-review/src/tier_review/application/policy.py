from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch

from tier_review.domain import Tier


@dataclass(frozen=True)
class ReviewPolicy:
    """Which files are tests, which are noise, and what to assume when we know nothing.

    Patterns are fnmatch globs matched against project-relative POSIX paths
    (`*` also matches `/`).
    """

    test_patterns: tuple[str, ...] = ("tests/*", "*/tests/*", "test_*.py", "*/test_*.py", "conftest.py", "*/conftest.py")
    ignore_patterns: tuple[str, ...] = ("*.md", "*.rst", "*.txt.example", ".gitignore")
    source_suffixes: tuple[str, ...] = (".py",)
    unknown_tier: Tier = Tier.CRITICAL  # anything we cannot attribute to a tiered test
    empty_change_tier: Tier = Tier.LOW  # a change with nothing relevant in it

    def is_test(self, path: str) -> bool:
        return _matches(path, self.test_patterns)

    def is_ignored(self, path: str) -> bool:
        return _matches(path, self.ignore_patterns)

    def is_source(self, path: str) -> bool:
        return path.endswith(self.source_suffixes)


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch(path, pattern) for pattern in patterns)
