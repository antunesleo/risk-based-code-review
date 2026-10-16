# tier-review

Decide which review change needs by mapping every changed line to error-impact tier of tests that execute it. Small Python package with CLI, pytest plugin, library API. Knows nothing about project it reviews.

| Tier | Errors... | Review |
|------|-----------|--------|
| **0** | can cause significant financial loss, expose sensitive data or violate regulations | human review by domain owner |
| **1** | affect important business flows, but impact limited or recoverable | human review |
| **2** | low impact, fixable without relevant consequences | automated review only |

## Install

Not on PyPI; install from local path:

```sh
pip install ./tier-review            # or "-e ./tier-review" while developing
```

In requirements file, add path relative to where pip runs. Example codebase does this in `example-codebase/requirements-dev.txt`:

```
../tier-review
```

Install registers `tier-review` command and pytest plugin, both via entry points in `pyproject.toml`.

## Use it

**1. Tag tests** with tier of flow they protect:

```python
@pytest.mark.tier(0)
def test_sla_credit_cannot_be_issued_twice(...): ...
```

**2. Catalog tiers** — line → tests (`LineTestCatalog`) and test → tier (`TestTierCatalog`), together `CatalogTiers`:

```sh
pytest --cov --cov-context=test --test-tiers=test-tiers.json --tier-strict
```

`--cov-context=test` makes coverage.py label every executed line with test that ran it. `--test-tiers` writes `test-tiers.json` (test id → tier); `--tier-strict` fails run if any test has no tier. Measure test code too (`source = app, tests` in `.coveragerc`) so test changes get classified.

Catalog twice: on base commit and on working tree.

**3. Classify the diff:**

```sh
tier-review classify --repo . --project example-codebase --base main \
    --line-tests head/.coverage --test-tiers head/test-tiers.json \
    --base-line-tests base/.coverage --base-test-tiers base/test-tiers.json \
    [--format json]
```

Prints tier, review route, deciding lines, tests behind each line. `--diff-file` reads unified diff instead of asking git. Base catalog optional, but without it any test change = tier 0 (see below).

From Python:

```python
from tier_review import CatalogTiers, ClassifyDiff
head = CatalogTiers(line_tests, test_tiers)
base = CatalogTiers(base_line_tests, base_test_tiers)
decision = ClassifyDiff(diff, head, scopes, base=base).execute()
decision.tier, decision.verdicts
```

## How it works inside

```
src/tier_review/
  classify.py           ClassifyDiff: the rules. CatalogTiers: one commit's two catalogs.
                          Also defines the interfaces it reads:
                          DiffSource, LineTestCatalog, TestTierCatalog, ScopeResolver
  tiers.py              Tier (0 critical, 1 important, 2 low) and its review route
  changes.py            ChangeSet > ChangedFile > ChangeBlock (new lines + the base lines they replace)
  decision.py           Decision > LineVerdict > Verdict (tier, Reason, tests)
  policy.py             ReviewPolicy: which paths are tests, docs, source; the fallback tier

  diff.py               DiffSource from `git diff -U0` or from text
  line_test_catalog.py  CoveragePyLineTestCatalog: LineTestCatalog from a coverage.py data file
  test_tier_catalog.py  JsonTestTierCatalog: TestTierCatalog from the plugin's JSON
  scopes.py             ScopeResolver: innermost enclosing function, via the stdlib AST

  pytest_plugin.py      @pytest.mark.tier -> test-tiers.json
  report.py             text and JSON rendering
  cli.py                argument parsing; builds the readers and runs ClassifyDiff
```

`classify.py` is core. Depends only on value types (`tiers`, `changes`, `decision`, `policy`) and interfaces it declares. Readers implement interfaces with real files; unit tests implement them with in-memory fakes (`tests/fakes.py`). Only `cli.py` wires readers and rules together.

### The rules

Per changed file and line, in order:

1. **Ignored** (`*.md`, ...) → skipped.
2. **Deleted, moved or non-Python application file** → tier 0; impact can't be traced.
3. **A changed line** takes most critical tier among
   - tests that execute it (or, if none, tests of enclosing function), and
   - tests that executed base lines it replaces or removes.

   Test counts with more critical of its base and head tier.
4. **Test module code no test executes** (imports, constants) → tests module defines, or every test below a `conftest.py`.
5. **Still nothing** → tier 0; no test would catch mistake.
6. **Test removed, or moved to less critical tier** → its base tier.

Blank lines not changes. Diff takes most critical tier across all its lines.

### Test code is classified too

Test line takes tier of tests that execute it. For test, that's itself; fixture takes most critical tier of tests using it. Diff shipping tier 1 feature with tier 1 test stays tier 1. Base catalog catches ways a diff could make code look safer than it is: retagging test, deleting it, or making code stop running under tier 0 test. Without base catalog those indistinguishable from ordinary edit, so any test change = tier 0.

## Develop

```sh
make test        # unit tests in Docker
make install     # pip install -e ".[dev]" into the current environment
make dev-test    # unit tests in the current environment
```
