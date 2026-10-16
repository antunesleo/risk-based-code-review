# example-codebase

Example source code of a helpdesk system, entangled on purpose (a big ball of mud). Customers open
tickets, agents reply, back office issues SLA credits and exports reports.

There are no real module boundaries: `helpers.py` and `sla.py` are shared by
ticketing, billing and reporting; `admin.py` puts a money endpoint next to a CSV
export; services raise HTTP errors and reach into the global `db.DB` dict.
That is the point: you cannot tell how risky a change is from the file it touches.

Every test carries `@pytest.mark.tier(N)` for the error-impact tier of the flow
it protects:

| Tier | Meaning | Tests here |
|------|---------|------------|
| 0 | financial loss, sensitive data exposure, regulatory violation | SLA credits, e-mail masking |
| 1 | important business flow, limited or recoverable impact | tickets, comments, customers |
| 2 | low impact, fixable without relevant consequences | CSV export, summary, health |
