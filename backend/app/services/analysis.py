"""Ingredient-list analysis.

Turns an ordered INCI list into the facts the product page and the recommender
both need: which actives are present, which irritants, how pore-clogging it is.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.services.inci import lookup

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Ingredients in the first ~8 INCI positions are present at meaningful levels.
# Past roughly position 15 most things are trace, so an "active" there is mostly
# label decoration - we still report it, but weight it far lower.
HIGH_POSITION_CUTOFF = 8


@lru_cache(maxsize=1)
def config() -> dict:
    return json.loads((DATA_DIR / "conflicts.json").read_text(encoding="utf-8"))


@dataclass(slots=True)
class AnalyzedIngredient:
    position: int
    inci_name: str
    common_name: str | None = None
    function: str | None = None
    is_active: bool = False
    is_irritant: bool = False
    comedogenic_rating: int | None = None
    active_group: str | None = None
    description: str | None = None
    known: bool = True

    @property
    def is_prominent(self) -> bool:
        return self.position <= HIGH_POSITION_CUTOFF


@dataclass(slots=True)
class Analysis:
    ingredients: list[AnalyzedIngredient] = field(default_factory=list)
    actives: list[AnalyzedIngredient] = field(default_factory=list)
    irritants: list[AnalyzedIngredient] = field(default_factory=list)
    active_groups: set[str] = field(default_factory=set)
    max_comedogenic: int = 0
    has_fragrance: bool = False
    has_alcohol: bool = False
    has_essential_oil: bool = False
    unknown_count: int = 0

    @property
    def known_count(self) -> int:
        return len(self.ingredients) - self.unknown_count

    def group_weight(self, group: str) -> float:
        """How strongly this product delivers a given active group.

        A retinoid at position 3 counts far more than one at position 22.
        """
        best = 0.0
        for ingredient in self.actives:
            if ingredient.active_group != group:
                continue
            weight = 1.0 if ingredient.is_prominent else 0.45
            best = max(best, weight)
        return best

    def has_ingredient(self, inci_name: str) -> bool:
        target = inci_name.lower()
        return any(i.inci_name.lower() == target for i in self.ingredients)

    def ingredient_weight(self, inci_name: str) -> float:
        target = inci_name.lower()
        for ingredient in self.ingredients:
            if ingredient.inci_name.lower() == target:
                return 1.0 if ingredient.is_prominent else 0.45
        return 0.0


FRAGRANCE_NAMES = {"fragrance", "parfum"}
ALCOHOL_NAMES = {"alcohol denat.", "ethanol"}
ESSENTIAL_OIL_MARKERS = ("oil",)
ESSENTIAL_OIL_NAMES = {
    "lavandula angustifolia oil",
    "melaleuca alternifolia leaf oil",
    "citrus limon peel oil",
    "mentha piperita oil",
    "eucalyptus globulus leaf oil",
}


def analyze(names: list[str]) -> Analysis:
    """Build the full analysis from an ordered INCI list."""
    result = Analysis()

    for index, name in enumerate(names, start=1):
        entry = lookup(name)
        if entry is None:
            analyzed = AnalyzedIngredient(position=index, inci_name=name, known=False)
            result.unknown_count += 1
        else:
            analyzed = AnalyzedIngredient(
                position=index,
                inci_name=entry["inci_name"],
                common_name=entry.get("common_name"),
                function=entry.get("function"),
                is_active=bool(entry.get("is_active")),
                is_irritant=bool(entry.get("is_irritant")),
                comedogenic_rating=entry.get("comedogenic_rating"),
                active_group=entry.get("active_group"),
                description=entry.get("description"),
                known=True,
            )

        result.ingredients.append(analyzed)

        if analyzed.is_active:
            result.actives.append(analyzed)
            if analyzed.active_group:
                result.active_groups.add(analyzed.active_group)
        if analyzed.is_irritant:
            result.irritants.append(analyzed)
        if analyzed.comedogenic_rating:
            result.max_comedogenic = max(result.max_comedogenic, analyzed.comedogenic_rating)

        lowered = analyzed.inci_name.lower()
        if lowered in FRAGRANCE_NAMES:
            result.has_fragrance = True
        if lowered in ALCOHOL_NAMES:
            result.has_alcohol = True
        if lowered in ESSENTIAL_OIL_NAMES:
            result.has_essential_oil = True

    return result


def detect_conflicts(analyses: list[tuple[str, Analysis]]) -> list[dict]:
    """Find conflicting actives across a set of products in one routine.

    `analyses` is [(product_label, Analysis)]. Returns one entry per rule that
    fires, naming the two products responsible so the UI can point at them.
    """
    rules = config()["conflict_rules"]
    findings: list[dict] = []

    for rule in rules:
        group_a, group_b = rule["groups"]
        holders_a = [label for label, a in analyses if group_a in a.active_groups]
        holders_b = [label for label, a in analyses if group_b in a.active_groups]
        if not holders_a or not holders_b:
            continue

        # A single product formulated with both is the brand's decision, and is
        # balanced as sold - only flag when two separate products collide.
        pairs = [(x, y) for x in holders_a for y in holders_b if x != y]
        if not pairs:
            continue

        first, second = pairs[0]
        findings.append(
            {
                "id": rule["id"],
                "severity": rule["severity"],
                "title": rule["title"],
                "explanation": rule["explanation"],
                "guidance": rule["guidance"],
                "products": [first, second],
            }
        )

    severity_order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: severity_order.get(f["severity"], 3))
    return findings
