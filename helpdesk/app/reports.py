from app import db, helpers, sla


def tickets_csv():
    rows = [["id", "subject", "priority", "customer", "created", "breached"]]
    for ticket in sorted(db.DB["tickets"].values(), key=lambda t: t["id"]):
        customer = db.DB["customers"].get(ticket["customer_id"], {})
        rows.append([
            ticket["id"],
            ticket["subject"],
            ticket["priority"],
            customer.get("name", ""),
            helpers.fmt_date(ticket["created_at"]),
            "yes" if sla.is_breached(ticket) else "no",
        ])
    return "\n".join(",".join(helpers.csv_escape(v) for v in row) for row in rows) + "\n"


def summary():
    counts = {priority: 0 for priority in helpers.PRIORITIES}
    for ticket in db.DB["tickets"].values():
        counts[helpers.normalize_priority(ticket["priority"])] += 1
    return {"total": sum(counts.values()), "by_priority": counts}
