from decimal import Decimal

from app import helpers, notifications, sla
from app.db import DB
from app.repositories import TicketRepository

CREDIT_RATE = {
    "low": Decimal("0.05"),
    "normal": Decimal("0.10"),
    "high": Decimal("0.20"),
    "urgent": Decimal("0.50"),
}


class BillingError(Exception):
    pass


def issue_sla_credit(ticket_id):
    ticket = TicketRepository().get(ticket_id)
    if ticket is None:
        raise LookupError(ticket_id)
    customer = DB["customers"][ticket["customer_id"]]
    if any(credit["ticket_id"] == ticket_id for credit in DB["credits"]):
        raise BillingError("ticket already credited")
    if not sla.is_breached(ticket):
        raise BillingError("SLA was not breached")
    priority = helpers.normalize_priority(ticket["priority"])
    amount = helpers.money(helpers.PLANS[customer["plan"]] * CREDIT_RATE[priority])
    credit = {"ticket_id": ticket_id, "customer_id": customer["id"], "amount": amount}
    DB["credits"].append(credit)
    notifications.notify(customer, "credit_issued", amount=amount, ticket_id=ticket_id)
    return credit
