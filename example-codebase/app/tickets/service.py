from fastapi import HTTPException

from app import db, helpers, notifications, sla
from app.customers import get_customer_or_404
from app.repositories import TicketRepository


def get_ticket_or_404(ticket_id):
    ticket = TicketRepository().get(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="ticket not found")
    return ticket


def create_ticket(data):
    customer = get_customer_or_404(data["customer_id"])
    try:
        priority = helpers.normalize_priority(data.get("priority"))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    created_at = helpers.now()
    ticket = {
        "id": db.next_id(),
        "customer_id": customer["id"],
        "subject": data["subject"],
        "body": data["body"],
        "priority": priority,
        "status": "open",
        "created_at": created_at,
        "due_at": sla.compute_due(customer["plan"], priority, created_at),
        "closed_at": None,
    }
    TicketRepository().add(ticket)
    notifications.notify(customer, "ticket_created", ticket_id=ticket["id"], subject=ticket["subject"])
    return ticket


def add_comment(ticket_id, author, body):
    ticket = get_ticket_or_404(ticket_id)
    comment = {"ticket_id": ticket_id, "author": author, "body": body, "created_at": helpers.now()}
    db.DB["comments"].append(comment)
    if author == "customer" and ticket["status"] == "closed":
        ticket["status"] = "open"
        ticket["closed_at"] = None
    if author == "agent":
        customer = db.DB["customers"][ticket["customer_id"]]
        notifications.notify(
            customer, "comment_added", ticket_id=ticket_id, when=helpers.fmt_date(comment["created_at"])
        )
    return comment


def close_ticket(ticket_id):
    ticket = get_ticket_or_404(ticket_id)
    ticket["status"] = "closed"
    ticket["closed_at"] = helpers.now()
    return ticket


def list_tickets(status=None):
    return sorted(TicketRepository().list(status), key=lambda t: t["created_at"], reverse=True)
