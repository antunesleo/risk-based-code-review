# example-codebase

Example helpdesk system source, entangled on purpose (big ball of mud). Customers open tickets, agents reply, back office issues SLA credits, exports reports.

No real module boundaries: `helpers.py` and `sla.py` shared by ticketing, billing, reporting; `admin.py` puts money endpoint next to CSV export; services raise HTTP errors, reach into global `db.DB` dict. That the point: can't tell change risk from file touched.

Every test carries `@pytest.mark.tier(N)` for error-impact tier of flow it protects:

| Tier | Meaning | Tests here |
|------|---------|------------|
| 0 | financial loss, sensitive data exposure, regulatory violation | SLA credits, e-mail masking |
| 1 | important business flow, limited or recoverable impact | tickets, comments, customers |
| 2 | low impact, fixable without relevant consequences | CSV export, summary, health |

## Run it

```sh
make test         # test suite in Docker
make up           # serve the API on :8000 (PORT=8089 make up)
```
