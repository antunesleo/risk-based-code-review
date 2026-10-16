"""The "database". A module-level dict that every other module imports and mutates."""
from itertools import count

DB = {
    "customers": {},
    "tickets": {},
    "comments": [],
    "credits": [],
    "outbox": [],
}

_ids = count(1)


def next_id():
    return next(_ids)


def reset():
    global _ids
    for table in DB.values():
        table.clear()
    _ids = count(1)
