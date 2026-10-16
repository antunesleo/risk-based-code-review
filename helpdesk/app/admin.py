"""Back-office endpoints. Money and spreadsheets, living together."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app import billing, reports

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/tickets/{ticket_id}/sla-credit", status_code=201)
def sla_credit(ticket_id: int):
    try:
        credit = billing.issue_sla_credit(ticket_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="ticket not found")
    except billing.BillingError as error:
        raise HTTPException(status_code=409, detail=str(error))
    return {"ticket_id": ticket_id, "amount": str(credit["amount"])}


@router.get("/reports/tickets.csv", response_class=PlainTextResponse)
def export_tickets():
    return PlainTextResponse(reports.tickets_csv(), media_type="text/csv")


@router.get("/reports/summary")
def report_summary():
    return reports.summary()
