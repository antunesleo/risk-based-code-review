from pydantic import BaseModel


class TicketIn(BaseModel):
    customer_id: int
    subject: str
    body: str
    priority: str | None = None


class CommentIn(BaseModel):
    author: str
    body: str
