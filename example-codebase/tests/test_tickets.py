import pytest

from app import db


@pytest.mark.tier(1)
def test_create_ticket_sets_due_date_from_plan_and_priority(client, seed_customer):
    customer = seed_customer(plan="enterprise")

    response = client.post(
        "/tickets", json={"customer_id": customer["id"], "subject": "Down", "body": "...", "priority": "P1"}
    )

    assert response.status_code == 201
    assert response.json()["priority"] == "urgent"
    assert response.json()["due_at"] == "2026-01-05T10:00:00+00:00"


@pytest.mark.tier(1)
def test_create_ticket_for_unknown_customer_returns_404(client):
    response = client.post("/tickets", json={"customer_id": 999, "subject": "?", "body": "..."})

    assert response.status_code == 404


@pytest.mark.tier(1)
def test_agent_comment_notifies_customer(client, seed_customer, seed_ticket):
    ticket = seed_ticket(seed_customer())

    client.post(f"/tickets/{ticket['id']}/comments", json={"author": "agent", "body": "On it"})

    assert db.DB["outbox"][-1]["body"] == f"New reply on #{ticket['id']} at 2026-01-05 09:00"


@pytest.mark.tier(1)
def test_customer_comment_reopens_closed_ticket(client, seed_customer, seed_ticket):
    ticket = seed_ticket(seed_customer())
    client.post(f"/tickets/{ticket['id']}/close")

    client.post(f"/tickets/{ticket['id']}/comments", json={"author": "customer", "body": "Still broken"})

    assert client.get(f"/tickets/{ticket['id']}").json()["status"] == "open"


@pytest.mark.tier(1)
def test_list_tickets_filters_by_status(client, seed_customer, seed_ticket):
    customer = seed_customer()
    open_ticket = seed_ticket(customer)
    seed_ticket(customer, status="closed")

    response = client.get("/tickets", params={"status": "open"})

    assert [t["id"] for t in response.json()] == [open_ticket["id"]]


@pytest.mark.tier(0)
def test_ticket_view_never_exposes_customer_email(client, seed_customer, seed_ticket):
    ticket = seed_ticket(seed_customer(email="grace@example.com"))

    response = client.get(f"/tickets/{ticket['id']}")

    assert "grace@example.com" not in response.text
    assert response.json()["customer"]["email"] == "g***@example.com"
