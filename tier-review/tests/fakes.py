from tier_review.domain import ChangeSet, Tier


class FakeDiff:
    def __init__(self, *files):
        self._changes = ChangeSet(tuple(files))

    def changes(self):
        return self._changes


class FakeCoverage:
    def __init__(self, lines: dict[tuple[str, int], set[str]]):
        self._lines = lines

    def tests_for(self, path, lines):
        return frozenset(t for line in lines for t in self._lines.get((path, line), ()))


class FakeCatalog:
    def __init__(self, tiers: dict[str, int]):
        self._tiers = {k: Tier(v) for k, v in tiers.items()}

    def tier_of(self, test_id):
        return self._tiers.get(test_id)


class FakeScopes:
    def __init__(self, scopes: dict[str, list[range]] | None = None):
        self._scopes = scopes or {}

    def enclosing_scope(self, path, line):
        return next((r for r in self._scopes.get(path, []) if line in r), None)
