from app import db


class CustomerRepository:
    def add(self, customer):
        db.DB["customers"][customer["id"]] = customer
        return customer

    def get(self, customer_id):
        return db.DB["customers"].get(customer_id)


class TicketRepository:
    def add(self, ticket):
        db.DB["tickets"][ticket["id"]] = ticket
        return ticket

    def get(self, ticket_id):
        return db.DB["tickets"].get(ticket_id)

    def list(self, status=None):
        tickets = list(db.DB["tickets"].values())
        if status:
            tickets = [t for t in tickets if t["status"] == status]
        return tickets
