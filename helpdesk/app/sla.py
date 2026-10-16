from datetime import timedelta

from app import helpers

SLA_HOURS = {
    "free": {"low": 72, "normal": 48, "high": 24, "urgent": 12},
    "pro": {"low": 48, "normal": 24, "high": 8, "urgent": 4},
    "enterprise": {"low": 24, "normal": 8, "high": 4, "urgent": 1},
}


def compute_due(plan, priority, created_at):
    return created_at + timedelta(hours=SLA_HOURS[plan][priority])


def is_breached(ticket, at=None):
    if ticket["status"] == "closed":
        return ticket["closed_at"] > ticket["due_at"]
    at = at or helpers.now()
    return at > ticket["due_at"]
