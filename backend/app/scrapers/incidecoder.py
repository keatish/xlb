"""INCIDecoder ingredient source.

Not a retailer - this supplies the full INCI list that the storefronts mostly do
not publish. Ingredient data is what powers the analysis panel, the dupe finder
and the conflict warnings, so it gets its own source rather than being a
best-effort scrape of marketing copy.

robots.txt permits /products/ and /search (only /auth/ and /products/recommend/
are disallowed), and that is enforced in fetch.py regardless.
"""

from __future__ import annotations

import logging
import re

from selectolax.parser import HTMLParser

from app.scrapers.fetch import fetch_text
from app.services.text import clean_product_name, normalize_text

logger = logging.getLogger(__name__)

BASE_URL = "https://incidecoder.com"


def _similarity(a: str, b: str) -> float:
    """Cheap token overlap - good enough to rank search hits."""
    at, bt = set(a.split()), set(b.split())
    if not at or not bt:
        return 0.0
    return len(at & bt) / len(at | bt)


async def search_products(query: str, limit: int = 8) -> list[tuple[str, str]]:
    """Return (title, slug) candidates for a product name."""
    html = await fetch_text(
        f"{BASE_URL}/search",
        params={"query": query},
        headers={"Accept": "text/html"},
    )
    tree = HTMLParser(html)
    seen: set[str] = set()
    results: list[tuple[str, str]] = []
    for anchor in tree.css("a"):
        href = anchor.attributes.get("href") or ""
        if not href.startswith("/products/"):
            continue
        slug = href.split("/products/", 1)[1].strip("/")
        if not slug or slug in seen:
            continue
        seen.add(slug)
        results.append((anchor.text(strip=True) or slug, slug))
        if len(results) >= limit:
            break
    return results


async def fetch_ingredients(slug: str) -> list[str]:
    """Ordered INCI list for one INCIDecoder product page.

    Order is preserved because INCI position approximates concentration - it is
    what makes the dupe scoring meaningful rather than a flat set comparison.
    """
    html = await fetch_text(
        f"{BASE_URL}/products/{slug}",
        headers={"Accept": "text/html"},
    )
    tree = HTMLParser(html)

    names: list[str] = []
    seen: set[str] = set()
    for link in tree.css("a.ingred-link"):
        name = link.text(strip=True)
        if not name:
            continue
        key = normalize_text(name)
        if not key or key in seen:
            continue
        seen.add(key)
        names.append(name)
    return names


async def find_ingredients_for(
    brand: str | None,
    product_name: str,
    min_similarity: float = 0.34,
) -> tuple[list[str], str | None]:
    """Best-effort lookup: search, pick the closest title, return its INCI list.

    Returns ([], None) rather than raising when nothing matches well enough - a
    missing ingredient list is a normal outcome, not an error.
    """
    query = " ".join(filter(None, [brand, product_name])).strip()
    if not query:
        return [], None

    try:
        candidates = await search_products(query)
    except Exception as exc:  # noqa: BLE001 - source is optional, never fatal
        logger.warning("incidecoder search failed for %r: %s", query, exc)
        return [], None

    if not candidates:
        return [], None

    target = clean_product_name(product_name, brand)
    if not target:
        target = normalize_text(product_name)

    best_slug: str | None = None
    best_score = 0.0
    for title, slug in candidates:
        candidate_text = clean_product_name(title, brand) or normalize_text(title)
        score = _similarity(target, candidate_text)
        # Slug often carries the brand, which is a useful extra signal.
        if brand and normalize_text(brand).replace(" ", "-") in slug:
            score += 0.15
        if score > best_score:
            best_score, best_slug = score, slug

    if not best_slug or best_score < min_similarity:
        logger.info(
            "no confident incidecoder match for %r (best score %.2f)", query, best_score
        )
        return [], None

    try:
        return await fetch_ingredients(best_slug), best_slug
    except Exception as exc:  # noqa: BLE001
        logger.warning("incidecoder fetch failed for %s: %s", best_slug, exc)
        return [], None
