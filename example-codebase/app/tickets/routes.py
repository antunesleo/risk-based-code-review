from fastapi import APIRouter

from app import db
from app.customers import public_view
from app.tickets import service
from app.tickets.schemas import CommentIn, TicketIn

router = APIRouter(prefix="/tickets", tags=["tickets"])


def serialize(ticket):
    return {
        "id": ticket["id"],
        "subject": ticket["subject"],
        "priority": ticket["priority"],
        "status": ticket["status"],
        "due_at": ticket["due_at"].isoformat(),
    }


@router.post("", status_code=201)
def create_ticket(payload: TicketIn):
    return serialize(service.create_ticket(payload.model_dump()))


@router.get("")
def list_tickets(status: str | None = None):
    return [serialize(t) for t in service.list_tickets(status)]


@router.get("/{ticket_id}")
def get_ticket(ticket_id: int):
    ticket = service.get_ticket_or_404(ticket_id)
    customer = db.DB["customers"][ticket["customer_id"]]
    comments = [c for c in db.DB["comments"] if c["ticket_id"] == ticket_id]
    return {
        **serialize(ticket),
        "customer": public_view(customer),
        "comments": [{"author": c["author"], "body": c["body"]} for c in comments],
    }


@router.post("/{ticket_id}/comments", status_code=201)
def add_comment(ticket_id: int, payload: CommentIn):
    comment = service.add_comment(ticket_id, payload.author, payload.body)
    return {"author": comment["author"], "body": comment["body"]}


@router.post("/{ticket_id}/close")
def close_ticket(ticket_id: int):
    return serialize(service.close_ticket(ticket_id))
