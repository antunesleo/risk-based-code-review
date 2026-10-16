import pytest


@pytest.mark.tier(0)
def test_customer_email_is_masked_in_public_view(client):
    created = client.post("/customers", json={"name": "Ada", "email": "ada@example.com", "plan": "pro"})

    response = client.get(f"/customers/{created.json()['id']}")

    assert response.json()["email"] == "a***@example.com"


@pytest.mark.tier(1)
def test_create_customer_rejects_unknown_plan(client):
    response = client.post("/customers", json={"name": "Ada", "email": "ada@example.com", "plan": "gold"})

    assert response.status_code == 422
