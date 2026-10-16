"""Things that didn't have a home. Used by ticketing, billing, reports, notifications..."""
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

PLANS = {"free": Decimal("0"), "pro": Decimal("49.00"), "enterprise": Decimal("499.00")}
PRIORITIES = ["low", "normal", "high", "urgent"]

_frozen_now = None


def now():
    return _frozen_now or datetime.now(timezone.utc)


def freeze_time(moment):
    global _frozen_now
    _frozen_now = moment


def normalize_priority(value):
    if value is None:
        return "normal"
    value = str(value).strip().lower()
    aliases = {"p1": "urgent", "p2": "high", "p3": "normal", "p4": "low"}
    value = aliases.get(value, value)
    if value not in PRIORITIES:
        raise ValueError(f"unknown priority {value!r}")
    return value


def mask_email(email):
    name, _, domain = email.partition("@")
    return f"{name[:1]}***@{domain}"


def money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def fmt_date(moment):
    return moment.strftime("%Y-%m-%d %H:%M")


def csv_escape(value):
    text = str(value)
    if any(char in text for char in ',"\n'):
        text = '"' + text.replace('"', '""') + '"'
    return text


def legacy_priority_from_v1(code):
    # Used once by a migration script in 2019. Nobody remembers. Nobody tests it.
    return {1: "urgent", 2: "high", 3: "normal"}.get(code, "low")
