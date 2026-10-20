# Risk-based code review

**Let your tests decide which pull requests need a human.**

This README is an article, and the repository is its working example. You can read it top
to bottom, or clone the repo and run every claim yourself.

## BLUF (bottom line up front)

1. **The problem:** code is being written faster than people can review it, and giving
   every pull request the same review either wastes reviewers or lets risky changes through.
2. **The proposal:** route each pull request by **risk**. Low-risk changes get automated
   review only, important ones get a human, and critical ones get the domain owner.
3. **Risk is a tier of error impact:** tier 0 means money, sensitive data or regulation;
   tier 1 means an important but recoverable flow; tier 2 means low impact.
4. **File paths can't tell you the tier.** In real codebases, one file often mixes features
   that move money or handle sensitive data with low-stakes ones like a report or a
   housekeeping task, and a helper that looks harmless can feed a critical flow.
5. **Tests can tell you the tier.** Tag each test with the tier of the flow it protects,
   record which tests execute each line, and give each changed line the most critical tier
   among its tests.
6. **Untested code is tier 0.** If no test runs a line, nothing would catch a mistake
   there, so a human has to look at it.
7. **Test code is classified too.** Retagging, deleting or weakening the coverage of a
   critical test keeps the critical tier, so a pull request can't make itself look safe.
8. **It's a tool you can run:** `tier-review` is a Python CLI and pytest plugin. It's
   demonstrated here on a deliberately tangled helpdesk app with 12 example changes.
9. **It has known limits:** it can't see assertion strength, and it's only as good as the
   tests and their tiers.

> [!WARNING]
> **This is a proof of concept, not a product.** The code was vibe-coded (written mostly
> with an AI coding assistant) to demonstrate the idea, and it hasn't been hardened,
> reviewed or tested beyond this demo. Don't use it to gate real pull requests. Take the
> idea, and build your own implementation if it fits your team.

## The problem: review doesn't scale

A team ships a small pull request on a Friday:

```diff
-    return at > ticket["due_at"]
+    return at >= ticket["due_at"]
```

The description says it fixes an edge case in the SLA report: "this only feeds the export
column". The diff is one character long, in a file called `sla.py`, and the reviewer approves it.

The same function also decides whether a customer gets an **SLA credit**, which is money.
Starting Monday, tickets closed exactly at their deadline get credited.

Nothing in the diff said "billing". The reviewer would have needed to know every caller of
that function. In a codebase without real module boundaries, nobody knows all the callers.

At the same time, the amount of code to review keeps growing. Coding agents open pull
requests in parallel, and most of those changes really are trivial. Teams end up with two bad options:

- **Review everything carefully.** Reviewers become the bottleneck, and they start skimming.
- **Auto-approve the "small" changes.** The one-character change above is small.

What teams need is a reliable answer to one question: **how much review does this specific
change need?**

## The idea: ask the tests

The usual answer is path rules, such as "`billing/**` needs the payments team"
(CODEOWNERS). Path rules work when the code is organized by risk. Most code isn't
organized that way: helpers, shared rules and mixed-purpose files cross every boundary.

Tests already encode which behavior matters. A test named
`test_sla_credit_cannot_be_issued_twice` protects a money flow. So you can tag tests and
let coverage connect them to code:

| Tier | Errors in this flow... | Review route |
|------|------------------------|--------------|
| **0** | can cause significant financial loss, expose sensitive data or violate regulations | human review by the domain owner |
| **1** | affect important business flows, but the impact is limited or recoverable | human review |
| **2** | have low impact and can be fixed without relevant consequences | automated review only |

```python
@pytest.mark.tier(0)
def test_sla_credit_cannot_be_issued_twice(...): ...
```

Then three steps, each one mechanical:

1. **Record** which tests execute each line (coverage with per-test contexts).
2. **Chain** each changed line to its tests, and each test to its tier.
3. **Decide**: a line takes the most critical tier of its tests, and the pull request takes
   the most critical tier of its lines. A line that no test runs is tier 0.

Applied to the Friday pull request, the tool flags it as tier 0:

```
REVIEW TIER 0 (CRITICAL): human review by a domain owner is required

Why:
  app/sla.py:20  executed by tests
      tier 0  tests/test_billing.py::test_sla_credit_cannot_be_issued_twice
      tier 0  tests/test_billing.py::test_sla_credit_is_issued_for_breached_ticket
      tier 0  tests/test_billing.py::test_sla_credit_is_refused_when_sla_was_not_breached
      tier 2  tests/test_reports.py::test_tickets_csv_export
```

The export test is there, as the author said. So are three billing tests.

The decision is made **per line, not per file**. In the same codebase, a change to the CSV
export route in `app/admin.py`, the file that also issues credits, is tier 2:

```
REVIEW TIER 2 (LOW): eligible for automated review only

Why:
  app/admin.py:23  executed by tests
      tier 2  tests/test_reports.py::test_tickets_csv_export
```

## Try it yourself

You need `git`, `make` and Docker. Everything runs in containers.

```sh
git clone https://github.com/antunesleo/risk-based-code-review.git
cd risk-based-code-review
```

### 1. Watch the demo (about 2 minutes)

```sh
make demo
```

This applies each change in [`demo/scenarios/`](demo/scenarios), classifies it, and
reverts it. Your working tree has to be clean first.

| # | Change (paths under `example-codebase/`) | Tier | Why |
|---|------------------------------------------|------|-----|
| 01 | `app/reports.py:12`: null-safe customer name | **2** | only the CSV export test runs it |
| 02 | `app/admin.py:23`: CSV `charset=utf-8` | **2** | same file as the money endpoint, different code path |
| 03 | `app/admin.py:17`: reword the 409 credit-conflict message | **0** | SLA credit tests run it |
| 04 | `app/helpers.py:41`: `fmt_date` as an f-string | **1** | comment notifications (1) and the export (2) share it |
| 05 | `app/tickets/service.py:61`: sort tickets by `(created_at, id)` | **1** | ticket list test |
| 06 | `app/sla.py:20`: `>` becomes `>=` (the Friday pull request) | **0** | "only feeds the export column", but billing uses it too |
| 07 | `app/helpers.py:53`: default priority `"low"` → `"normal"` | **0** | no test executes it |
| 08 | `tests/test_reports.py:32-35`: stronger health check | **2** | only the tier 2 health test runs it |
| 09 | `README.md:5`: reword a sentence | **2** | nothing relevant changed |
| 10 | `tests/test_billing.py:6`: `tier(0)` → `tier(2)` | **0** | a downgraded test keeps its base tier |
| 11 | `tests/test_billing.py:28-36`: delete a tier 0 test | **0** | the removed test protected a tier 0 flow |
| 12 | `app/tickets/service.py:61` + a new tier 1 test | **1** | code and test both belong to tier 1 flows |

Scenarios 02/03 and 04/07 touch the same files and get different tiers.

### 2. Make your own change

Edit anything under `example-codebase/`, then run:

```sh
make review
```

This catalogs your working tree and `HEAD`, then classifies `git diff HEAD`. The output
shows the tier, the review route, the lines that set the tier and the tests behind each line.

Guess the tier before you run it, then check your guess:

<details>
<summary>Change any line in <code>app/billing.py</code></summary>

**Tier 0.** It's the money flow.
</details>

<details>
<summary>Change <code>fmt_date</code> in <code>app/helpers.py</code></summary>

**Tier 1.** Comment notifications (tier 1) and the export (tier 2) use it.
</details>

<details>
<summary>Change the CSV header in <code>app/reports.py</code></summary>

**Tier 2.** Only the export depends on it.
</details>

<details>
<summary>Add an assertion to <code>test_health</code> in <code>tests/test_reports.py</code></summary>

**Tier 2.** Only that tier 2 test runs the line.
</details>

<details>
<summary>Retag a billing test from <code>tier(0)</code> to <code>tier(2)</code></summary>

**Tier 0.** A test keeps the more critical of its old and new tiers.
</details>

Other things to try: delete a test, add a function nobody calls, edit `tests/conftest.py`,
or combine several changes. If an edit breaks a test, the catalog warns you, and each
test keeps the lines it reached before failing. A test without `@pytest.mark.tier` stops
the catalog with an error.

Reset when you're done (this discards your edits):

```sh
git checkout -- example-codebase && git clean -fd example-codebase
```

Variants:

```sh
make review BASE=main          # diff against another ref, e.g. a branch's commits
make review FORMAT=json        # machine-readable decision, e.g. for CI
```

### 3. Run each step by hand

`make review` runs three `tier-review` commands. You can run them yourself with
`make tier-review -- <args>`. The `--` stops make from reading the flags as its own.

```sh
make tier-review -- catalog --out .tier-review/head              # catalog the working tree
make tier-review -- catalog --out .tier-review/base --ref HEAD   # catalog the base commit
make tier-review -- classify --base HEAD \
    --catalog .tier-review/head --base-catalog .tier-review/base  # classify the diff
make tier-review -- catalog --out .tier-review/head -- -k billing  # args after the 2nd -- go to pytest
make tier-review -- classify --help                              # all options
```

The catalogs are written to `.tier-review/`, which is gitignored. You can inspect
`test-tiers.json`, or open `.coverage` with coverage.py. Re-catalog the head after each edit.

## How it works

**Catalog.** `tier-review catalog` runs the project's test suite and writes two files:

- `.coverage`: line → tests that executed it. This comes from pytest-cov with
  `--cov-context=test`, and covers both app code and test code.
- `test-tiers.json`: test → tier. The pytest plugin writes it from the `@pytest.mark.tier` markers.

It does this twice: once for the working tree (head) and once for the base commit (`--ref`).

**Classify.** `tier-review classify` reads the diff and, for each changed line, takes the
most critical tier among:

- the tests that execute it now, or the tests of its enclosing function for a new line
  that no test runs yet;
- the tests that executed the base lines it replaces or removes.

A line with no tests at all is tier 0. Deleted, moved or non-Python application files are
tier 0, because their impact can't be traced. Docs are ignored. The pull request takes the
most critical tier across all of its lines.

The full rules, the package layout and the Python API are in
[tier-review/README.md](tier-review/README.md).

## Test code needs review too

The tiers are only as trustworthy as the tests behind them. A pull request that edits tests
is editing the safety net, so a weakened assertion in an SLA credit test is a tier 0 risk
even if no app line changed.

The tool treats test lines like app lines. A test line takes the tier of the tests that
execute it, and a fixture takes the most critical tier of the tests using it. So a pull
request that ships a tier 1 feature with its tier 1 test stays tier 1.

Comparing against the base catalog closes the ways a pull request could make code look safer
than it is:

- **Retagging** a test from `tier(0)` to `tier(2)` keeps tier 0 (scenario 10).
- **Deleting a test** keeps the tier it had on base (scenario 11).
- **Removing coverage** doesn't help: code that tier 0 tests used to run stays tier 0 even
  if the pull request stops them from running it.

Without a base catalog, the tool can't tell an edit from a downgrade, so any test change is tier 0.

## Where this applies

The example is a "big ball of mud" monolith because that's where path rules fail most
visibly. The approach isn't limited to monoliths:

- **Shared code in any codebase**, such as utilities, middleware and base classes, crosses
  module boundaries the way `helpers.py` does here.
- **Test changes** need the same protection in every project.
- **Well-bounded modules** can often use path rules instead. There, this approach works as
  a check that the boundaries really hold.
- **Microservices** are covered within each service. A change that breaks another service
  through an API is only caught if a test exercises that path with coverage.

## Known limits

The tool is deliberately conservative: when it's unsure, it picks tier 0.

- **Catalog lag.** The demo builds both catalogs from scratch, so the results are exact. In
  real CI with a slow suite, keep a catalog built on `main` after each merge as the base, and
  only build the head catalog in pull requests. Rebuild on every merge, not nightly.
- **Import-time code.** Module-level statements (constants like `SLA_HOURS`) run during
  test collection, outside any test, so they can't be attributed and fall to tier 0.
- **Fixtures count.** Code that runs in test setup or teardown is attributed to that test.
  That's why the tier 0 tests in the example seed data straight into the database instead of
  going through the ticket API. Otherwise ticket creation would inherit tier 0.
- **Assertion strength is invisible.** A weakened tier 2 test is still a tier 2 change.
  That's acceptable by definition, and tier 0 tests always get owner review.
- **Coverage isn't correctness.** A line run only by tier 2 tests can still break a tier 0
  flow that no test exercises. The tool is only as good as the suite and its tiers.

## What's in the repository

```
example-codebase/  a helpdesk (support ticket) API in FastAPI, tangled on purpose.
                   Every test is tagged @pytest.mark.tier(0|1|2). See its README.
tier-review/       the tool: a Python package (CLI, pytest plugin, library) with its own
                   tests. The example codebase installs it from this local path.
demo/scenarios/    the 12 example changes, as patches
scripts/demo.sh    the demo runner
```

## Background

This repository grew out of the discussion on
[Automated code review, service tiers and multiple parallel agents](https://dev.to/antunesleo/automated-code-review-service-tiers-and-multiple-parallel-agents-weekly-reflections-2-3n2k).
