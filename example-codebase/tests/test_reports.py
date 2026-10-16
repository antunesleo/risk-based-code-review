import pytest


@pytest.mark.tier(2)
def test_tickets_csv_export(client, seed_customer, seed_ticket):
    customer = seed_customer(name="Ada, Countess")
    seed_ticket(customer, subject="Login", age_hours=2, sla_hours=1)

    response = client.get("/admin/reports/tickets.csv")

    assert response.headers["content-type"].startswith("text/csv")
    assert response.text.splitlines() == [
        "id,subject,priority,customer,created,breached",
        '2,Login,normal,"Ada, Countess",2026-01-05 07:00,yes',
    ]


@pytest.mark.tier(2)
def test_summary_counts_tickets_by_priority(client, seed_customer, seed_ticket):
    customer = seed_customer()
    seed_ticket(customer, priority="urgent")
    seed_ticket(customer, priority="low")

    response = client.get("/admin/reports/summary")

    assert response.json()["total"] == 2
    assert response.json()["by_priority"]["urgent"] == 1


@pytest.mark.tier(2)
def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
