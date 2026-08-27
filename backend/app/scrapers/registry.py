"""Retailer registry.

Adding a Shopify retailer is one entry here. Adding a non-Shopify retailer is a
new RetailerScraper subclass plus one entry. Nothing else in the system needs to
know a new source exists.

Every retailer listed here was checked against its robots.txt before inclusion,
and fetch.py re-checks on every request.
"""

from __future__ import annotations

from app.scrapers.base import RetailerScraper
from app.scrapers.shopify import ShopifyRetailer, ShopifyScraper

SHOPIFY_RETAILERS: list[ShopifyRetailer] = [
    ShopifyRetailer(
        key="sokoglam",
        display_name="Soko Glam",
        domain="sokoglam.com",
        currency="USD",
    ),
    ShopifyRetailer(
        key="ohlolly",
        display_name="Ohlolly",
        domain="www.ohlolly.com",
        currency="USD",
    ),
]

# Retailers deliberately excluded, kept here so the reasoning is not lost:
#
#   stylevana.com  - robots.txt names ClaudeBot with Disallow: / and blocks
#                    */catalogsearch/result/ for every agent.
#   yesstyle.com   - robots.txt blocks /*?q* (all search URLs) and the product
#                    REST API. Product pages are permitted, so it can be added
#                    later using sitemap-based discovery instead of search.
#   target.com     - RedSky API returns 403 without an approved key.
#   oliveyoung, iherb, skinsort - 403 to any non-browser client.
EXCLUDED_RETAILERS: dict[str, str] = {
    "stylevana": "robots.txt disallows ClaudeBot sitewide and blocks catalogsearch",
    "yesstyle": "robots.txt blocks search URLs; product pages permitted via sitemap",
    "target": "RedSky API requires an approved key",
    "oliveyoung": "returns 403 to non-browser clients",
    "iherb": "returns 403 to non-browser clients",
}


def build_scrapers() -> dict[str, RetailerScraper]:
    return {cfg.key: ShopifyScraper(cfg) for cfg in SHOPIFY_RETAILERS}


SCRAPERS: dict[str, RetailerScraper] = build_scrapers()


def get_scraper(key: str) -> RetailerScraper:
    try:
        return SCRAPERS[key]
    except KeyError:
        raise KeyError(f"unknown retailer {key!r}; known: {sorted(SCRAPERS)}") from None


def retailer_seed() -> list[dict]:
    """Rows for seeding the `retailer` table."""
    return [
        {
            "name": cfg.display_name,
            "slug": cfg.key,
            "base_url": f"https://{cfg.domain}",
            "scraper_key": cfg.key,
        }
        for cfg in SHOPIFY_RETAILERS
    ]
