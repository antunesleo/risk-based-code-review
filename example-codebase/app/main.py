from fastapi import FastAPI

from app import admin, customers
from app.tickets import routes as tickets

app = FastAPI(title="Helpdesk (a big ball of mud)")
app.include_router(customers.router)
app.include_router(tickets.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"status": "ok"}
