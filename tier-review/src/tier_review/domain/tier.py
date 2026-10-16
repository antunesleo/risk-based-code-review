from __future__ import annotations

from collections.abc import Iterable
from enum import IntEnum


class Tier(IntEnum):
    """Error-impact tier. Lower value means a mistake costs more."""

    CRITICAL = 0  # financial loss, sensitive data exposure, regulatory violation
    IMPORTANT = 1  # important business flow affected, limited or recoverable impact
    LOW = 2  # low impact, fixable without relevant consequences

    @classmethod
    def parse(cls, value: int | str) -> Tier:
        try:
            return cls(int(value))
        except (TypeError, ValueError):
            raise ValueError(f"invalid tier {value!r}; expected one of {[t.value for t in cls]}") from None

    @classmethod
    def most_critical(cls, tiers: Iterable[Tier], default: Tier | None = None) -> Tier:
        tiers = list(tiers)
        if not tiers:
            if default is None:
                raise ValueError("no tiers given and no default")
            return default
        return min(tiers)

    @property
    def review_route(self) -> str:
        return _ROUTES[self]


_ROUTES = {
    Tier.CRITICAL: "human review by a domain owner is required",
    Tier.IMPORTANT: "human review is required",
    Tier.LOW: "eligible for automated review only",
}
