"""Customer routes, schemas and logic. Also imported by the ticket service, because why not."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import db, helpers
from app.repositories import CustomerRepository

router = APIRouter(prefix="/customers", tags=["customers"])


class CustomerIn(BaseModel):
    name: str
    email: str
    plan: str = "free"


def get_customer_or_404(customer_id):
    customer = CustomerRepository().get(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="customer not found")
    return customer


def public_view(customer):
    return {
        "id": customer["id"],
        "name": customer["name"],
        "email": helpers.mask_email(customer["email"]),
        "plan": customer["plan"],
    }


@router.post("", status_code=201)
def create_customer(payload: CustomerIn):
    if payload.plan not in helpers.PLANS:
        raise HTTPException(status_code=422, detail=f"unknown plan {payload.plan}")
    customer = {"id": db.next_id(), **payload.model_dump()}
    CustomerRepository().add(customer)
    return public_view(customer)


@router.get("/{customer_id}")
def get_customer(customer_id: int):
    return public_view(get_customer_or_404(customer_id))
