"""Quiz-driven recommendation scoring.

Deliberately rule-based and additive rather than learned: every point a product
scores can be traced to a specific ingredient, so the UI can always answer "why
am I being shown this?". That explanation is the feature - a black-box ranker
would be worse here even if it ranked slightly better.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.analysis import Analysis, config

# Relative pull of each signal. Concern match dominates: it is what the user
# actually asked for.
W_CONCERN = 3.0
W_SKIN_TYPE = 2.0
W_BUDGET = 1.0
W_AVAILABILITY = 0.5
PENALTY_IRRITANT = 4.0
PENALTY_COMEDOGENIC = 2.5


@dataclass(slots=True)
class SkinProfile:
    skin_type: str = "normal"
    concerns: list[str] = field(default_factory=list)
    sensitive: bool = False
    acne_prone: bool = False
    fragrance_free: bool = False
    budget_max: float | None = None
    categories: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ScoredProduct:
    product_id: int
    score: float
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _entry_weight(analysis: Analysis, entry: dict) -> float:
    """How strongly a product satisfies one concern/preference entry."""
    if "group" in entry:
        return analysis.group_weight(entry["group"]) * entry.get("weight", 1.0)
    if "inci" in entry:
        return analysis.ingredient_weight(entry["inci"]) * entry.get("weight", 1.0)
    return 0.0


def _describe(entry: dict, analysis: Analysis) -> str | None:
    """Name the specific ingredient responsible, not the rule that fired."""
    if "inci" in entry:
        return entry["inci"]
    group = entry.get("group")
    if not group:
        return None
    for ingredient in analysis.actives:
        if ingredient.active_group == group:
            return ingredient.common_name or ingredient.inci_name
    return None


def score_product(
    product_id: int,
    analysis: Analysis,
    profile: SkinProfile,
    price: float | None = None,
    in_stock: bool = True,
    concern_labels: dict[str, str] | None = None,
) -> ScoredProduct:
    cfg = config()
    concern_map = cfg["concern_ingredients"]
    type_prefs = cfg["skin_type_preferences"]
    labels = concern_labels or {c["key"]: c["label"] for c in cfg["concerns"]}

    result = ScoredProduct(product_id=product_id, score=0.0)

    # 1. Concern match - the main event.
    for concern in profile.concerns:
        entries = concern_map.get(concern, [])
        best_weight = 0.0
        best_entry: dict | None = None
        for entry in entries:
            weight = _entry_weight(analysis, entry)
            if weight > best_weight:
                best_weight, best_entry = weight, entry
        if best_weight > 0 and best_entry is not None:
            result.score += W_CONCERN * best_weight
            name = _describe(best_entry, analysis)
            label = labels.get(concern, concern).lower()
            if name:
                result.reasons.append(f"Contains {name}, which targets {label}")

    # 2. Skin-type fit.
    prefs = type_prefs.get(profile.skin_type, {"prefer": [], "avoid": []})
    for entry in prefs.get("prefer", []):
        weight = _entry_weight(analysis, entry)
        if weight > 0:
            result.score += W_SKIN_TYPE * weight * 0.5
            name = _describe(entry, analysis)
            if name and len(result.reasons) < 5:
                result.reasons.append(f"{name} suits {profile.skin_type} skin")
    for entry in prefs.get("avoid", []):
        weight = _entry_weight(analysis, entry)
        if weight > 0:
            result.score -= W_SKIN_TYPE * weight
            name = _describe(entry, analysis)
            if name:
                result.warnings.append(f"Contains {name}, often poor for {profile.skin_type} skin")

    # 3. Sensitivity penalties. Applied on top of skin-type rules because a user
    #    can be, say, oily AND reactive.
    if profile.sensitive:
        if analysis.has_fragrance:
            result.score -= PENALTY_IRRITANT
            result.warnings.append("Contains fragrance, a common irritant for sensitive skin")
        if analysis.has_alcohol:
            result.score -= PENALTY_IRRITANT * 0.75
            result.warnings.append("Contains denatured alcohol, which can be drying")
        if analysis.has_essential_oil:
            result.score -= PENALTY_IRRITANT * 0.75
            result.warnings.append("Contains essential oils, a frequent sensitiser")
        other_irritants = [
            i for i in analysis.irritants
            if i.inci_name.lower() not in {"fragrance", "parfum", "alcohol denat.", "ethanol"}
            and i.is_prominent
        ]
        result.score -= min(len(other_irritants), 3) * 0.75

    elif profile.fragrance_free and analysis.has_fragrance:
        result.score -= PENALTY_IRRITANT * 0.5
        result.warnings.append("Contains fragrance")

    # 4. Comedogenic penalty for acne-prone skin.
    if profile.acne_prone and analysis.max_comedogenic >= 3:
        result.score -= PENALTY_COMEDOGENIC * (analysis.max_comedogenic - 2) / 3
        offender = max(
            (i for i in analysis.ingredients if (i.comedogenic_rating or 0) >= 3),
            key=lambda i: i.comedogenic_rating or 0,
            default=None,
        )
        if offender:
            result.warnings.append(
                f"{offender.inci_name} is rated {offender.comedogenic_rating}/5 for clogging pores"
            )

    # 5. Budget and availability.
    if profile.budget_max is not None and price is not None:
        if price <= profile.budget_max:
            result.score += W_BUDGET
        else:
            over = (price - profile.budget_max) / max(profile.budget_max, 1.0)
            result.score -= W_BUDGET * min(over, 2.0)
            result.warnings.append(f"Above your ${profile.budget_max:.0f} budget")

    if in_stock:
        result.score += W_AVAILABILITY
    else:
        result.score -= W_AVAILABILITY
        result.warnings.append("Currently out of stock")

    result.score = round(result.score, 3)
    return result


def rank(
    scored: list[ScoredProduct],
    limit: int = 20,
    min_score: float = 0.5,
) -> list[ScoredProduct]:
    """Highest score first, dropping products with nothing to recommend them."""
    keep = [s for s in scored if s.score >= min_score and s.reasons]
    keep.sort(key=lambda s: (-s.score, s.product_id))
    return keep[:limit]


# Order products should be applied in. Used to turn a flat recommendation list
# into a routine the user can actually follow.
ROUTINE_ORDER = [
    "cleanser",
    "exfoliant",
    "toner",
    "essence",
    "serum",
    "treatment",
    "eye_cream",
    "moisturizer",
    "sunscreen",
    "mask",
]


def routine_position(category: str) -> int:
    try:
        return ROUTINE_ORDER.index(category)
    except ValueError:
        return len(ROUTINE_ORDER)


def build_routine(items: list[tuple[int, str]]) -> dict[str, list[int]]:
    """Split recommended products into AM and PM routines.

    Exfoliants and retinoid-style treatments go to PM; sunscreen is AM-only.
    Everything else appears in both, in application order.
    """
    ordered = sorted(items, key=lambda pair: routine_position(pair[1]))
    am: list[int] = []
    pm: list[int] = []
    for product_id, category in ordered:
        if category == "sunscreen":
            am.append(product_id)
        elif category in {"exfoliant", "treatment"}:
            pm.append(product_id)
        else:
            am.append(product_id)
            pm.append(product_id)
    return {"am": am, "pm": pm}
