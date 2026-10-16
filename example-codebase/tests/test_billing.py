import pytest

from app import db


@pytest.mark.tier(0)
def test_sla_credit_is_issued_for_breached_ticket(client, seed_customer, seed_ticket):
    customer = seed_customer(plan="pro")
    ticket = seed_ticket(customer, priority="urgent", age_hours=10, sla_hours=4)

    response = client.post(f"/admin/tickets/{ticket['id']}/sla-credit")

    assert response.status_code == 201
    assert response.json() == {"ticket_id": ticket["id"], "amount": "24.50"}
    assert db.DB["outbox"][-1]["template"] == "credit_issued"


@pytest.mark.tier(0)
def test_sla_credit_is_refused_when_sla_was_not_breached(client, seed_customer, seed_ticket):
    ticket = seed_ticket(seed_customer(), age_hours=1, sla_hours=24)

    response = client.post(f"/admin/tickets/{ticket['id']}/sla-credit")

    assert response.status_code == 409
    assert db.DB["credits"] == []


@pytest.mark.tier(0)
def test_sla_credit_cannot_be_issued_twice(client, seed_customer, seed_ticket):
    ticket = seed_ticket(seed_customer(), age_hours=30, sla_hours=24)
    client.post(f"/admin/tickets/{ticket['id']}/sla-credit")

    response = client.post(f"/admin/tickets/{ticket['id']}/sla-credit")

    assert response.status_code == 409
    assert len(db.DB["credits"]) == 1
