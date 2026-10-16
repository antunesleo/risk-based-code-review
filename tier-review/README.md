# tier-review

Decides which review a change needs by mapping every changed line to the
error-impact tier of the tests that execute it. It is a small Python package with
a CLI, a pytest plugin and a library API. It knows nothing about the project it
reviews.

| Tier | Errors... | Review |
|------|-----------|--------|
| **0** | can cause significant financial loss, expose sensitive data or violate regulations | human review by a domain owner |
| **1** | affect important business flows, but the impact is limited or recoverable | human review |
| **2** | have low impact and can be fixed without relevant consequences | automated review only |

## Install

It is not on PyPI; install it from a local path:

```sh
pip install ./tier-review            # or "-e ./tier-review" while developing
```

In a requirements file, add the path relative to where pip runs. The example codebase
does this in `example-codebase/requirements-dev.txt`:

```
../tier-review
```

Installing it registers the `tier-review` command and the pytest plugin, both
through entry points in `pyproject.toml`.

## Use it

**1. Tag tests** with the tier of the flow they protect:

```python
@pytest.mark.tier(0)
def test_sla_credit_cannot_be_issued_twice(...): ...
```

**2. Record a map**, which records which test ran each line and the tier of each test:

```sh
pytest --cov --cov-context=test --tier-catalog=test-tiers.json --tier-strict
```

`--cov-context=test` makes coverage.py label every executed line with the test that
ran it. `--tier-catalog` writes `test-tiers.json` (test id → tier), and `--tier-strict`
fails the run if any test has no tier. Measure test code too (`source = app, tests` in
`.coveragerc`) so that test changes can be classified.

Record it twice: on the base commit and on the change.

**3. Classify the diff:**

```sh
tier-review classify --repo . --project example-codebase --base main \
    --coverage head/.coverage --catalog head/test-tiers.json \
    --base-coverage base/.coverage --base-catalog base/test-tiers.json \
    [--format json]
```

It prints the tier, the review route, the lines that decided it and the tests behind
each line. `--diff-file` reads a unified diff instead of asking git. The base map is
optional, but without it any test change is tier 0 (see below).

From Python:

```python
from tier_review import BaseMap, ClassifyChange
decision = ClassifyChange(diff, coverage, catalog, scopes, base=BaseMap(base_coverage, base_catalog)).execute()
decision.tier, decision.verdicts
```

## How it works inside

```
src/tier_review/
  classify.py        ClassifyChange: the rules. Also defines the four interfaces it reads:
                       DiffSource, CoverageIndex, TierCatalog, ScopeResolver
  tiers.py           Tier (0 critical, 1 important, 2 low) and its review route
  changes.py         ChangeSet > ChangedFile > ChangeBlock (new lines + the base lines they replace)
  decision.py        Decision > LineVerdict > Verdict (tier, Reason, tests)
  policy.py          ReviewPolicy: which paths are tests, docs, source; the fallback tier

  diff.py            DiffSource from `git diff -U0` or from text
  coverage_index.py  CoverageIndex from a coverage.py data file with test contexts
  catalog.py         TierCatalog from the JSON written by the plugin
  scopes.py          ScopeResolver: innermost enclosing function, via the stdlib AST

  pytest_plugin.py   @pytest.mark.tier -> test-tiers.json
  report.py          text and JSON rendering
  cli.py             argument parsing; builds the readers and runs ClassifyChange
```

`classify.py` is the core. It depends only on the value types (`tiers`, `changes`,
`decision`, `policy`) and on the interfaces it declares. The readers implement those
interfaces with real files, and the unit tests implement them with in-memory fakes
(`tests/fakes.py`). Only `cli.py` puts the readers and the rules together.

### The rules

For each changed file and line, in order:

1. **Ignored** (`*.md`, ...) → skipped.
2. **Deleted, moved or non-Python application file** → tier 0, because its impact
   can't be traced.
3. **A changed line** takes the most critical tier among
   - the tests that execute it (or, if none do, the tests of its enclosing function), and
   - the tests that executed the base lines it replaces or removes.

   A test counts with the more critical of its base and head tier.
4. **Test module code no test executes** (imports, constants) → the tests the module
   defines, or every test below a `conftest.py`.
5. **Still nothing** → tier 0, because no test would catch a mistake.
6. **A test removed, or moved to a less critical tier** → its base tier.

Blank lines are not changes. The change takes the most critical tier across all of
its lines.

### Test code is classified too

A test line takes the tier of the tests that execute it. For a test, that is the test
itself; a fixture takes the most critical tier of the tests that use it. A PR that
ships a tier 1 feature with its tier 1 test therefore stays tier 1. The base map
catches the ways a PR could make code look safer than it is: retagging a test,
deleting it, or making code stop running under a tier 0 test. Without a base map
those can't be told apart from an ordinary edit, so any test change is tier 0.

## Develop

```sh
make test        # unit tests in Docker
make install     # pip install -e ".[dev]" into the current environment
make dev-test    # unit tests in the current environment
```
