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

1. **Map.** The example codebase's suite runs with pytest-cov recording *which test* executed every
   line, application and test code, and the tier-review pytest plugin writing which tier
   each test has. This happens twice: on the base commit (`make map-base`) and on the
   working tree (`make map`).
2. **Classify.** `tier-review classify` gives each changed line the most critical tier of
   the tests that run it, now or on the base. A line no test reaches is tier 0, because
   no test would catch a mistake there. The change takes the most critical tier of its
   lines.

The full rules, and how the package is built, are in
[tier-review/README.md](tier-review/README.md).

## Run it

Everything runs in Docker. The tool classifies your working-tree changes against git
(`BASE`, default `HEAD`).

```sh
make demo         # map HEAD, then apply each scenario, map it, classify, revert (needs a clean tree)
make review       # map BASE and the working tree, classify your changes (BASE=main for a branch)
make test         # example codebase tests
make tool-test    # tier-review unit tests
make up           # serve the helpdesk on :8000 (HELPDESK_PORT=8089 make up)
```

`docker compose run --rm tier-review classify ... --format json` emits a machine-readable
decision for CI.

## What the demo shows

The decision is per line, not per file. Each scenario changes a single line
(paths relative to `example-codebase/`):

| Scenario | Changed line | Change | Decision | Why |
|----------|--------------|--------|----------|-----|
| 01 reports refactor | `app/reports.py:12` | `customer.get("name") or ""` | **2** | only the CSV export test runs it |
| 02 admin export route | `app/admin.py:23` | CSV `media_type` gets `charset=utf-8` | **2** | same file as the money endpoint, different code path |
| 03 admin credit route | `app/admin.py:17` | reword the 409 credit conflict message | **0** | the SLA credit tests run it |
| 04 date format helper | `app/helpers.py:41` | `fmt_date` as an f-string | **1** | comment notifications (1) and export (2) share it |
| 05 ticket listing | `app/tickets/service.py:61` | sort tickets by `(created_at, id)` | **1** | ticket list test |
| 06 SLA breach rule | `app/sla.py:20` | `at > due_at` → `at >= due_at` | **0** | "it only feeds the export column", but billing uses it too |
| 07 legacy helper | `app/helpers.py:53` | default priority `"low"` → `"normal"` | **0** | no test executes it |
| 08 test edit | `tests/test_reports.py:32-35` | stronger health check assertions | **2** | only the (tier 2) health check test runs it |
| 09 docs only | `README.md:9` | reword a sentence | **2** | nothing relevant changed |
| 10 test retag | `tests/test_billing.py:6` | `@pytest.mark.tier(0)` → `tier(2)` | **0** | a test moved to a less critical tier keeps its base tier |
| 11 test removed | `tests/test_billing.py:28-36` | delete a tier 0 SLA credit test | **0** | the removed test protected a tier 0 flow |
| 12 feature with test | `app/tickets/service.py:61` + `tests/test_tickets.py:56-63` | stable ordering and a new tier 1 test | **1** | code and test both belong to tier 1 flows |

Scenarios 02/03 and 04/07 show the point: the **same file** lands in different tiers
depending on which line changed. Scenarios 08 and 10–12 show the same for test code.

## Test code has a tier too

The tiers are only as trustworthy as the tests behind them, so a PR that edits tests is
editing the safety net of the flows they protect. That makes **reviewing tests as
important as reviewing the code**: a weakened assertion in an SLA credit test is a tier 0
risk, even if no application line changed.

The tool treats test code like application code. A test line takes the tier of the tests
that execute it (a fixture takes the most critical tier of the tests using it), so a PR
that ships a tier 1 feature with its tier 1 test stays tier 1. The base map closes the ways
a PR could make code look safer than it is:

- **Retagging** `@pytest.mark.tier(0)` → `tier(2)` keeps tier 0 (scenario 10).
- **Deleting a test** takes the tier it had on the base (scenario 11).
- **Removing coverage**: code that tier 0 tests used to run stays tier 0 even if the PR
  stops them from running it.

Without a base map (`--base-coverage`, `--base-catalog`), the tool can't tell an edit from
a downgrade, so any test change falls back to tier 0.

## Known limits (deliberately conservative)

- **Map lag.** The demo builds both maps from scratch, so it is exact. In a real CI with
  a slow suite you would keep the map built on `main` after each merge as the base map and
  only build the head map in pull requests. Skip the head map too and new lines rely on
  enclosing-function inheritance, and a change that makes a tier 0 flow reach a helper
  goes unnoticed until the next map. Rebuild on every merge, not nightly.
- **Import-time code.** Module-level statements (constants like `SLA_HOURS`) run during
  test collection, outside any test, so they are unattributable and fall to tier 0.
- **Fixtures count.** Code that runs in a test's setup or teardown is attributed to that
  test. The example codebase's tier 0 tests seed data directly into the DB instead of going through
  the ticket API. Otherwise ticket creation would inherit tier 0.
- **Assertion strength is invisible.** A weakened tier 2 test is still a tier 2 change.
  That's acceptable by definition, and tier 0 tests always need an owner's review.
- **Coverage is not correctness.** A line executed by a tier 2 test can still break a
  tier 0 flow that no test exercises. The tool can only be as good as the suite's tiers.
