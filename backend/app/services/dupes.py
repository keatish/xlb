"""Dupe finding - cheaper products with a similar ingredient profile.

Plain Jaccard over ingredient sets does not work here: every product shares
water, glycerin and phenoxyethanol, so everything looks like a dupe of
everything. Two corrections make it meaningful:

  1. Weight by INCI position, since order approximates concentration.
  2. Require the actives to overlap. Two moisturizers with identical bases but
     different actives are different products, not dupes.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.analysis import Analysis

# Ubiquitous ingredients carry no signal about whether two products are alike.
COMMON_BASE = {
    "water", "glycerin", "butylene glycol", "phenoxyethanol", "ethylhexylglycerin",
    "disodium edta", "xanthan gum", "carbomer", "sodium hydroxide", "citric acid",
    "1,2-hexanediol", "propanediol", "dipropylene glycol", "chlorphenesin",
    "potassium sorbate", "sodium benzoate", "pentylene glycol",
}


@dataclass(slots=True)
class DupeScore:
    product_id: int
    similarity: float
    shared_actives: list[str]
    price: float | None = None
    savings: float | None = None


def _position_weight(position: int) -> float:
    """Weight by INCI position - top of the list counts far more."""
    if position <= 3:
        return 1.0
    if position <= 8:
        return 0.7
    if position <= 15:
        return 0.4
    return 0.15


def _weighted_profile(analysis: Analysis) -> dict[str, float]:
    profile: dict[str, float] = {}
    for ingredient in analysis.ingredients:
        key = ingredient.inci_name.lower()
        if key in COMMON_BASE:
            continue
        profile[key] = max(profile.get(key, 0.0), _position_weight(ingredient.position))
    return profile


def similarity(a: Analysis, b: Analysis) -> float:
    """Weighted Jaccard over the meaningful part of two ingredient lists."""
    pa, pb = _weighted_profile(a), _weighted_profile(b)
    if not pa or not pb:
        return 0.0

    keys = set(pa) | set(pb)
    intersection = sum(min(pa.get(k, 0.0), pb.get(k, 0.0)) for k in keys)
    union = sum(max(pa.get(k, 0.0), pb.get(k, 0.0)) for k in keys)
    if union == 0:
        return 0.0
    return round(intersection / union, 4)


def shared_actives(a: Analysis, b: Analysis) -> list[str]:
    names_a = {i.inci_name for i in a.actives}
    names_b = {i.inci_name for i in b.actives}
    return sorted(names_a & names_b)


def find_dupes(
    target_id: int,
    target: Analysis,
    target_price: float | None,
    target_category: str,
    candidates: list[tuple[int, Analysis, float | None, str]],
    min_similarity: float = 0.28,
    limit: int = 8,
    cheaper_only: bool = True,
) -> list[DupeScore]:
    """Rank candidates as dupes of the target.

    `candidates` is [(product_id, analysis, price, category)].
    """
    target_groups = {i.active_group for i in target.actives if i.active_group}
    results: list[DupeScore] = []

    for product_id, analysis, price, category in candidates:
        if product_id == target_id:
            continue
        # A cleanser is never a dupe of a serum, however similar the INCI list.
        if category != target_category:
            continue
        if cheaper_only and target_price is not None and price is not None and price >= target_price:
            continue

        candidate_groups = {i.active_group for i in analysis.actives if i.active_group}
        # If the target has actives, a dupe must deliver at least one of them.
        if target_groups and not (target_groups & candidate_groups):
            continue

        score = similarity(target, analysis)
        if score < min_similarity:
            continue

        savings = None
        if target_price is not None and price is not None:
            savings = round(target_price - price, 2)

        results.append(
            DupeScore(
                product_id=product_id,
                similarity=score,
                shared_actives=shared_actives(target, analysis),
                price=price,
                savings=savings,
            )
        )

    results.sort(key=lambda d: (-d.similarity, -(d.savings or 0)))
    return results[:limit]
