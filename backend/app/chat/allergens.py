"""Allergen resolution and product filtering for the chat assistant.

Avoidance is enforced *here*, in ordinary code, and applied to every product a
tool is about to hand back to the model. The model never sees an unfiltered list
and has no parameter it can set to relax the filter. That is deliberate: a chat
assistant that "forgets" a stated allergy is the one failure this feature cannot
have, and asking a language model to remember a constraint is not the same as
enforcing it.

Two kinds of allergen are supported, because users state both:

  - a named ingredient ("salicylic acid", "vitamin B3"), resolved against the
    INCI dictionary through the same canonicalizer the rest of the app uses; and
  - a whole class ("fragrance", "essential oils", "alcohol"), which maps onto
    the flags `Analysis` already computes.

Anything we cannot resolve is reported back rather than dropped, so the UI can
tell the user plainly that a term was not understood instead of implying it is
being filtered on.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.analysis import Analysis
from app.services.inci import canonicalize, ingredient_dictionary
from app.services.text import normalize_text

# Class-level allergens. Each maps to an attribute on Analysis, which is already
# populated during ingredient analysis, so there is nothing to recompute.
GROUP_FLAGS: dict[str, str] = {
    "fragrance": "has_fragrance",
    "essential_oil": "has_essential_oil",
    "alcohol": "has_alcohol",
}

GROUP_LABELS: dict[str, str] = {
    "fragrance": "fragrance",
    "essential_oil": "essential oils",
    "alcohol": "drying alcohol",
}

# The words people actually type, mapped onto those classes.
GROUP_SYNONYMS: dict[str, str] = {
    "fragrance": "fragrance",
    "fragrances": "fragrance",
    "parfum": "fragrance",
    "perfume": "fragrance",
    "perfumes": "fragrance",
    "scent": "fragrance",
    "scented": "fragrance",
    "essential oil": "essential_oil",
    "essential oils": "essential_oil",
    "eo": "essential_oil",
    "alcohol": "alcohol",
    "alcohols": "alcohol",
    "denatured alcohol": "alcohol",
    "alcohol denat": "alcohol",
    "ethanol": "alcohol",
}

# A term shorter than this is too ambiguous to substring-match on - "oil" would
# knock out most of the catalog.
MIN_SUBSTRING_LENGTH = 5


@dataclass(slots=True)
class ResolvedAllergens:
    """What the user's avoid-list actually resolved to."""

    inci_names: set[str] = field(default_factory=set)
    groups: set[str] = field(default_factory=set)
    unresolved: list[str] = field(default_factory=list)

    @property
    def active(self) -> bool:
        return bool(self.inci_names or self.groups)

    def labels(self) -> list[str]:
        """Human-readable list of what is being filtered, for the UI and the model."""
        out = [GROUP_LABELS[g] for g in sorted(self.groups) if g in GROUP_LABELS]
        out.extend(sorted(self.inci_names))
        return out


def _match_dictionary(term: str) -> set[str]:
    """Find INCI names matching a free-text term.

    Exact canonicalization first, since that is the precise path. Only when that
    fails do we fall back to substring matching over INCI and common names,
    which is how "vitamin c" or "niacinamide" typed loosely still lands.
    """
    canonical = canonicalize(term)
    table = ingredient_dictionary()

    if canonical:
        entry = table.get(normalize_text(canonical))
        if entry is not None:
            return {entry["inci_name"]}

    needle = normalize_text(term)
    if len(needle) < MIN_SUBSTRING_LENGTH:
        return set()

    hits: set[str] = set()
    for entry in table.values():
        haystacks = [normalize_text(entry["inci_name"])]
        if entry.get("common_name"):
            haystacks.append(normalize_text(entry["common_name"]))
        if any(needle in h for h in haystacks):
            hits.add(entry["inci_name"])
    return hits


def resolve(terms: list[str] | None) -> ResolvedAllergens:
    """Turn whatever the user said into something we can filter on."""
    resolved = ResolvedAllergens()
    if not terms:
        return resolved

    for raw in terms:
        term = (raw or "").strip()
        if not term:
            continue

        group = GROUP_SYNONYMS.get(normalize_text(term))
        if group:
            resolved.groups.add(group)
            continue

        hits = _match_dictionary(term)
        if hits:
            resolved.inci_names |= hits
        else:
            resolved.unresolved.append(term)

    return resolved


def blocked_reason(analysis: Analysis, resolved: ResolvedAllergens) -> str | None:
    """Why this product is unsuitable, or None if it is fine.

    Returning the reason rather than a bool is what lets the assistant say "I
    skipped three products because they contain fragrance" instead of silently
    showing a shorter list.
    """
    if not resolved.active:
        return None

    for group in sorted(resolved.groups):
        flag = GROUP_FLAGS.get(group)
        if flag and getattr(analysis, flag, False):
            return f"contains {GROUP_LABELS[group]}"

    if resolved.inci_names:
        wanted = {normalize_text(n) for n in resolved.inci_names}
        for ingredient in analysis.ingredients:
            if normalize_text(ingredient.inci_name) in wanted:
                return f"contains {ingredient.common_name or ingredient.inci_name}"

    return None
