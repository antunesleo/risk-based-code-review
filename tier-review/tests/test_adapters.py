from tier_review.adapters.python_scopes import AstScopeResolver
from tier_review.adapters.tier_catalog import JsonTierCatalog
from tier_review.domain import Tier

SOURCE = """\
LIMIT = 3


@decorator
def outer():
    x = 1

    def inner():
        return x

    return inner
"""


def test_scope_resolver_returns_innermost_function_including_decorators(tmp_path):
    (tmp_path / "mod.py").write_text(SOURCE)
    resolver = AstScopeResolver(tmp_path)

    assert resolver.enclosing_scope("mod.py", 4) == range(4, 12)
    assert resolver.enclosing_scope("mod.py", 9) == range(8, 10)
    assert resolver.enclosing_scope("mod.py", 1) is None


def test_tier_catalog_round_trips(tmp_path):
    path = tmp_path / "tiers.json"
    JsonTierCatalog({"tests/test_a.py::test_x": Tier.CRITICAL}).dump(path)

    catalog = JsonTierCatalog.load(path)

    assert catalog.tier_of("tests/test_a.py::test_x") is Tier.CRITICAL
    assert catalog.tier_of("unknown") is None
