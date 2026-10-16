"""TierCatalog backed by the JSON file written by the tier-review pytest plugin."""
from __future__ import annotations

import json
from pathlib import Path

from tier_review.tiers import Tier

FORMAT_VERSION = 1


class JsonTierCatalog:
    def __init__(self, tiers: dict[str, Tier]):
        self._tiers = dict(tiers)

    @classmethod
    def load(cls, path: Path) -> JsonTierCatalog:
        document = json.loads(path.read_text())
        if document.get("version") != FORMAT_VERSION:
            raise ValueError(f"{path}: unsupported tier catalog version {document.get('version')!r}")
        return cls({test_id: Tier.parse(tier) for test_id, tier in document["tests"].items()})

    def tier_of(self, test_id: str) -> Tier | None:
        return self._tiers.get(test_id)

    def test_ids(self) -> frozenset[str]:
        return frozenset(self._tiers)

    def dump(self, path: Path) -> None:
        document = {"version": FORMAT_VERSION, "tests": {k: int(v) for k, v in sorted(self._tiers.items())}}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document, indent=2) + "\n")

    def __len__(self) -> int:
        return len(self._tiers)
