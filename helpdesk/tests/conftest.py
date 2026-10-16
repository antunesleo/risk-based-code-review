from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import db, helpers
from app.main import app

NOW = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def clean_state():
    db.reset()
    helpers.freeze_time(NOW)
    yield
    helpers.freeze_time(None)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def seed_customer():
    """Writes straight into the in-memory DB, skipping the API on purpose."""

    def _seed(plan="pro", email="ada@example.com", name="Ada"):
        customer = {"id": db.next_id(), "name": name, "email": email, "plan": plan}
        db.DB["customers"][customer["id"]] = customer
        return customer

    return _seed


@pytest.fixture
def seed_ticket():
    def _seed(customer, priority="normal", age_hours=1, sla_hours=24, status="open", subject="Help"):
        created_at = NOW - timedelta(hours=age_hours)
        ticket = {
            "id": db.next_id(),
            "customer_id": customer["id"],
            "subject": subject,
            "body": "...",
            "priority": priority,
            "status": status,
            "created_at": created_at,
            "due_at": created_at + timedelta(hours=sla_hours),
            "closed_at": None,
        }
        db.DB["tickets"][ticket["id"]] = ticket
        return ticket

    return _seed
