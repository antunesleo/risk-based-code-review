# monolith-review

Exploring how to support automatic and semi-automatic code review: deciding which review
a pull request needs when the codebase is a **big ball of mud**, coupled, entangled code
with no real module boundaries.

This repository is a working demonstration of the idea discussed in the comments of
[Automated code review, service tiers and multiple parallel agents](https://dev.to/antunesleo/automated-code-review-service-tiers-and-multiple-parallel-agents-weekly-reflections-2-3n2k):
in a monolith you can't tell a change's risk from the file it touches, so **let the tests
tell you**. Tag each test with the error-impact tier of the flow it protects, record which
test executes each line, and give a change the most critical tier of any test that runs
the changed lines.

| Tier | Errors... | Review |
|------|-----------|--------|
| **0** | can cause significant financial loss, expose sensitive data or violate regulations | human review by a domain owner |
| **1** | affect important business flows, but the impact is limited or recoverable | human review |
| **2** | have low impact and can be fixed without relevant consequences | automated review only |

## Repository layout

```
helpdesk/      the big ball of mud: a small, deliberately entangled support ticket
               system (FastAPI, in-memory data), every test tagged @pytest.mark.tier(0|1|2)
tier-review/   the decision tool, independent of the helpdesk:
                 domain/        Tier, ChangeSet, Verdict, Decision (pure values)
                 ports.py       DiffSource, CoverageIndex, TierCatalog, ScopeResolver
                 application/   ClassifyChange (the rules) + ReviewPolicy
                 adapters/      git diff, coverage.py contexts, JSON catalog, AST scopes
                 collectors/    pytest plugin: @pytest.mark.tier -> test-tiers.json
                 cli.py         composition root
demo/          scenario patches, each a one-line change, that show the tool deciding
scripts/       demo runner
```

## How it works

1. **Map** (`make map`): the helpdesk suite runs with
   `pytest --cov --cov-context=test --tier-catalog=... --tier-strict`.
   - pytest-cov records *which test* executed every line (coverage.py dynamic contexts).
   - The tier-review pytest plugin writes `test-tiers.json` (test id → tier) and fails the
     run if any test has no tier.
2. **Classify** (`make review`): `tier-review classify` reads the git diff and, for each
   changed line:
   1. ignored file (`*.md`, ...) → skip
   2. a test file changed → **tier 0**, because it rewrites the map itself
   3. deleted, moved or non-Python file → **tier 0**, because its impact can't be traced
   4. line executed by tests → the most critical tier among those tests
   5. line not executed (new line, comment, signature) → inherits the tests of its
      enclosing function
   6. still nothing → **tier 0**, because no test would catch a mistake

   The change gets the most critical tier across all of its lines.

## Run it

Everything runs in Docker. The tool classifies your working-tree changes against git
(`BASE`, default `HEAD`).

```sh
make demo         # apply each scenario, rebuild the map, classify, revert (needs a clean tree)
make review       # classify your own working-tree changes (BASE=main for a branch)
make test         # helpdesk tests
make tool-test    # tier-review unit tests
make up           # serve the helpdesk on :8000 (HELPDESK_PORT=8089 make up)
```

`docker compose run --rm tier-review classify ... --format json` emits a machine-readable
decision for CI.

## What the demo shows

The decision is per line, not per file. Each scenario changes a single line
(paths relative to `helpdesk/`):

| Scenario | Changed line | Change | Decision | Why |
|----------|--------------|--------|----------|-----|
| 01 reports refactor | `app/reports.py:12` | `customer.get("name") or ""` | **2** | only the CSV export test runs it |
| 02 admin export route | `app/admin.py:23` | CSV `media_type` gets `charset=utf-8` | **2** | same file as the money endpoint, different code path |
| 03 admin credit route | `app/admin.py:17` | reword the 409 credit conflict message | **0** | the SLA credit tests run it |
| 04 date format helper | `app/helpers.py:41` | `fmt_date` as an f-string | **1** | comment notifications (1) and export (2) share it |
| 05 ticket listing | `app/tickets/service.py:61` | sort tickets by `(created_at, id)` | **1** | ticket list test |
| 06 SLA breach rule | `app/sla.py:20` | `at > due_at` → `at >= due_at` | **0** | "it only feeds the export column", but billing uses it too |
| 07 legacy helper | `app/helpers.py:53` | default priority `"low"` → `"normal"` | **0** | no test executes it |
| 08 test edit | `tests/test_reports.py:32` | stronger health check assertions | **0** | changing a test changes the map |
| 09 docs only | `README.md:9` | reword a sentence | **2** | nothing relevant changed |

Scenarios 02/03 and 04/07 show the point: the **same file** lands in different tiers
depending on which line changed.

## Known limits (deliberately conservative)

- **Map lag.** The demo rebuilds the map from the working tree, so it is exact. In a real
  CI with a slow suite you would build it on `main` after each merge and only query it in
  pull requests. New lines then rely on enclosing-function inheritance, and a merge that
  makes a tier 0 flow reach a helper is invisible until the map is rebuilt. Rebuild on
  every merge, not nightly.
- **Import-time code.** Module-level statements (constants like `SLA_HOURS`) run during
  test collection, outside any test, so they are unattributable and fall to tier 0.
- **Fixtures count.** Code that runs in a test's setup or teardown is attributed to that
  test. The helpdesk's tier 0 tests seed data directly into the DB instead of going through
  the ticket API. Otherwise ticket creation would inherit tier 0.
- **Coverage is not correctness.** A line executed by a tier 2 test can still break a
  tier 0 flow that no test exercises. The tool can only be as good as the suite's tiers.
