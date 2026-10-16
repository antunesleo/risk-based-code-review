# monolith-review

Explore auto and semi-auto code review: decide which review PR needs when codebase is **big ball of mud**, coupled, entangled code, no real module boundaries.

Repo = working demo of idea from comments of
[Automated code review, service tiers and multiple parallel agents](https://dev.to/antunesleo/automated-code-review-service-tiers-and-multiple-parallel-agents-weekly-reflections-2-3n2k):
in monolith, can't tell change risk from file touched, so **let tests tell you**. Tag each test with error-impact tier of flow it protects, record which test executes each line, give change most critical tier of any test running changed lines.

| Tier | Errors... | Review |
|------|-----------|--------|
| **0** | can cause significant financial loss, expose sensitive data or violate regulations | human review by domain owner |
| **1** | affect important business flows, but the impact is limited or recoverable | human review |
| **2** | have low impact and can be fixed without relevant consequences | automated review only |

## Repository layout

```
example-codebase/  the big ball of mud: example source code of a helpdesk (support ticket)
                   system, FastAPI with in-memory data, entangled on purpose. Every test
                   is tagged @pytest.mark.tier(0|1|2)
tier-review/       the decision tool: a Python package (CLI + pytest plugin + library) with
                   its own tests, Makefile and README. The example codebase installs it
                   from this local path. How it works inside: tier-review/README.md
demo/              scenario patches, each a small change, that show the tool deciding
scripts/           demo runner
```

## How it works

1. **Map.** Example codebase suite runs with pytest-cov recording *which test* executed every
   line (app and test code), and tier-review pytest plugin writing each test's tier.
   Happens twice: on base commit (`make map-base`) and on working tree (`make map`).
2. **Classify.** `tier-review classify` gives each changed line most critical tier of
   tests running it, now or on base. Line no test reaches = tier 0, since no test would
   catch mistake there. Change takes most critical tier of its lines.

Full rules and package build in
[tier-review/README.md](tier-review/README.md).

## Run it

All runs in Docker. Tool classifies working-tree changes against git (`BASE`, default `HEAD`).

```sh
make demo         # map HEAD, then apply each scenario, map it, classify, revert (needs a clean tree)
make review       # map BASE and the working tree, classify your changes (BASE=main for a branch)
make test         # example codebase tests
make tool-test    # tier-review unit tests
make up           # serve the helpdesk on :8000 (HELPDESK_PORT=8089 make up)
```

`docker compose run --rm tier-review classify ... --format json` emits machine-readable decision for CI.

## What the demo shows

Decision per line, not per file. Each scenario = small change
(paths relative to `example-codebase/`):

| Scenario | Changed line | Change | Decision | Why |
|----------|--------------|--------|----------|-----|
| 01 reports refactor | `app/reports.py:12` | `customer.get("name") or ""` | **2** | only CSV export test runs it |
| 02 admin export route | `app/admin.py:23` | CSV `media_type` gets `charset=utf-8` | **2** | same file as money endpoint, different code path |
| 03 admin credit route | `app/admin.py:17` | reword 409 credit conflict message | **0** | SLA credit tests run it |
| 04 date format helper | `app/helpers.py:41` | `fmt_date` as f-string | **1** | comment notifications (1) and export (2) share it |
| 05 ticket listing | `app/tickets/service.py:61` | sort tickets by `(created_at, id)` | **1** | ticket list test |
| 06 SLA breach rule | `app/sla.py:20` | `at > due_at` → `at >= due_at` | **0** | "only feeds export column", but billing uses it too |
| 07 legacy helper | `app/helpers.py:53` | default priority `"low"` → `"normal"` | **0** | no test executes it |
| 08 test edit | `tests/test_reports.py:32-35` | stronger health check assertions | **2** | only (tier 2) health check test runs it |
| 09 docs only | `README.md:5` | reword sentence | **2** | nothing relevant changed |
| 10 test retag | `tests/test_billing.py:6` | `@pytest.mark.tier(0)` → `tier(2)` | **0** | test moved to less critical tier keeps base tier |
| 11 test removed | `tests/test_billing.py:28-36` | delete tier 0 SLA credit test | **0** | removed test protected tier 0 flow |
| 12 feature with test | `app/tickets/service.py:61` + `tests/test_tickets.py:56-63` | stable ordering + new tier 1 test | **1** | code and test both belong to tier 1 flows |

Scenarios 02/03 and 04/07 show point: **same file** lands in different tiers depending on changed line. Scenarios 08 and 10–12 show same for test code.

## Test code has a tier too

Tiers only as trustworthy as tests behind them, so PR editing tests edits safety net of flows they protect. So **reviewing tests as important as reviewing code**: weakened assertion in SLA credit test = tier 0 risk, even if no app line changed.

Tool treats test code like app code. Test line takes tier of tests executing it (fixture takes most critical tier of tests using it), so PR shipping tier 1 feature with its tier 1 test stays tier 1. Base map closes ways PR could make code look safer than it is:

- **Retagging** `@pytest.mark.tier(0)` → `tier(2)` keeps tier 0 (scenario 10).
- **Deleting a test** takes tier it had on base (scenario 11).
- **Removing coverage**: code tier 0 tests used to run stays tier 0 even if PR stops them running it.

Without base map (`--base-coverage`, `--base-catalog`), tool can't tell edit from downgrade, so any test change falls back to tier 0.

## Known limits (deliberately conservative)

- **Map lag.** Demo builds both maps from scratch, so exact. Real CI with slow suite: keep map built on `main` after each merge as base map, only build head map in PRs. Skip head map too and new lines rely on enclosing-function inheritance; change making tier 0 flow reach helper goes unnoticed until next map. Rebuild every merge, not nightly.
- **Import-time code.** Module-level statements (constants like `SLA_HOURS`) run during test collection, outside any test, so unattributable, fall to tier 0.
- **Fixtures count.** Code running in test setup/teardown attributed to that test. Example codebase tier 0 tests seed data straight into DB instead of via ticket API. Otherwise ticket creation would inherit tier 0.
- **Assertion strength is invisible.** Weakened tier 2 test still tier 2 change. Acceptable by definition, and tier 0 tests always need owner review.
- **Coverage is not correctness.** Line run by tier 2 test can still break tier 0 flow no test exercises. Tool only as good as suite's tiers.
