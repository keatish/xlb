"""Cross-retailer product matching.

The core problem of price comparison: deciding that a listing on retailer A and a
listing on retailer B are the same physical product. Getting this wrong shows a
user the wrong price, which is worse than showing no price at all - so anything
below the confidence threshold is stored but hidden from the public price table.
"""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from app.models.enums import Category, MatchMethod
from app.services.text import (
    clean_product_name,
    normalize_brand,
    parse_pack_count,
    sizes_match,
)

# Shopify product_type values vary per store, so we map on substrings rather than
# exact values. Order matters: the first hit wins, so specific comes before broad.
CATEGORY_PATTERNS: list[tuple[tuple[str, ...], Category]] = [
    (("sunscreen", "sun stick", "spf", "suncare", "sun cream"), Category.SUNSCREEN),
    (("eye cream", "eye care", "eye serum", "eye patch"), Category.EYE_CREAM),
    (("exfoliant", "peeling", "scrub", "aha", "bha", "pha"), Category.EXFOLIANT),
    (("sheet mask", "mask", "pack"), Category.MASK),
    (("cleanser", "cleansing", "face wash", "foam", "oil cleanser", "balm"), Category.CLEANSER),
    (("toner", "tonic"), Category.TONER),
    (("essence",), Category.ESSENCE),
    (("serum", "ampoule", "booster"), Category.SERUM),
    (("moisturizer", "moisturiser", "cream", "lotion", "emulsion", "gel"), Category.MOISTURIZER),
    (("treatment", "spot", "acne", "patch"), Category.TREATMENT),
]


@dataclass(slots=True)
class MatchCandidate:
    """A normalized view of one listing, ready to compare."""

    brand: str
    name: str
    size_value: float | None
    size_unit: str | None
    upc: str | None
    pack_count: int = 1


@dataclass(slots=True)
class MatchResult:
    confidence: float
    method: MatchMethod
    matched: bool


def classify_category(product_type: str | None, title: str, tags: list[str] | None = None) -> Category:
    """Best-guess skincare category from whatever the retailer gave us."""
    haystack = " ".join(
        filter(None, [product_type or "", title or "", " ".join(tags or [])])
    ).lower()
    for needles, category in CATEGORY_PATTERNS:
        if any(needle in haystack for needle in needles):
            return category
    return Category.TREATMENT


def build_candidate(
    brand: str | None,
    title: str,
    size_value: float | None = None,
    size_unit: str | None = None,
    upc: str | None = None,
) -> MatchCandidate:
    return MatchCandidate(
        brand=normalize_brand(brand),
        name=clean_product_name(title, brand),
        size_value=size_value,
        size_unit=size_unit,
        upc=upc,
        pack_count=parse_pack_count(title),
    )


def compare(a: MatchCandidate, b: MatchCandidate, threshold: float = 0.85) -> MatchResult:
    """Decide whether two candidates are the same product.

    1. Identical barcodes are definitive - same GTIN means same SKU.
    2. Otherwise fuzzy-compare brand and name, gated on size and pack count.
    """
    if a.upc and b.upc and a.upc == b.upc:
        return MatchResult(confidence=1.0, method=MatchMethod.UPC, matched=True)

    # Different known barcodes mean different SKUs, whatever the titles say.
    if a.upc and b.upc and a.upc != b.upc:
        return MatchResult(confidence=0.0, method=MatchMethod.UPC, matched=False)

    if a.pack_count != b.pack_count:
        return MatchResult(confidence=0.0, method=MatchMethod.FUZZY, matched=False)

    if not sizes_match(a.size_value, a.size_unit, b.size_value, b.size_unit):
        return MatchResult(confidence=0.0, method=MatchMethod.FUZZY, matched=False)

    brand_score = fuzz.token_set_ratio(a.brand, b.brand) / 100 if a.brand and b.brand else 0.5
    if brand_score < 0.75:
        # Different brands are never the same product, however similar the name.
        return MatchResult(confidence=0.0, method=MatchMethod.FUZZY, matched=False)

    name_score = fuzz.token_set_ratio(a.name, b.name) / 100 if a.name and b.name else 0.0
    # Name carries most of the identity; brand is mostly a gate.
    confidence = round(0.75 * name_score + 0.25 * brand_score, 4)

    return MatchResult(
        confidence=confidence,
        method=MatchMethod.FUZZY,
        matched=confidence >= threshold,
    )


def best_match(
    candidate: MatchCandidate,
    existing: list[tuple[int, MatchCandidate]],
    threshold: float = 0.85,
) -> tuple[int | None, MatchResult]:
    """Find the best existing product for a new listing.

    Returns (product_id, result). product_id is None when nothing matched well
    enough, meaning the caller should create a new canonical product.
    """
    best_id: int | None = None
    best = MatchResult(confidence=0.0, method=MatchMethod.FUZZY, matched=False)

    for product_id, other in existing:
        result = compare(candidate, other, threshold=threshold)
        if result.confidence > best.confidence:
            best, best_id = result, product_id
        if result.method is MatchMethod.UPC and result.matched:
            return product_id, result

    if not best.matched:
        return None, best
    return best_id, best
