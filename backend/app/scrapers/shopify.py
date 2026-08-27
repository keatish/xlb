"""Generic Shopify storefront scraper.

Shopify exposes documented JSON endpoints on every storefront, so one class covers
every Shopify retailer. Adding a new one is a `ShopifyRetailer(...)` entry in the
registry - no new parsing code, which is the whole point of the base interface.

Endpoints used (all standard, all robots-checked before use):
  /search/suggest.json   - typeahead search
  /products/{handle}.json - full product record
  /products.json         - paginated catalog feed
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.scrapers.base import (
    ProductNotFound,
    RetailerScraper,
    ScrapedProduct,
    ScrapeFailed,
    SearchHit,
)
from app.scrapers.fetch import fetch_json
from app.services.text import parse_price, parse_size

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")


def html_to_text(html: str | None) -> str:
    if not html:
        return ""
    text = _TAG_RE.sub(" ", html)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
    )
    return re.sub(r"\s+", " ", text).strip()


def extract_ingredients(text: str) -> str | None:
    """Pull an INCI list out of a product description, if one is there at all.

    Most Shopify beauty listings do not include ingredients - that is why
    INCIDecoder exists as a separate source. This catches the ones that do.
    """
    if not text:
        return None
    match = re.search(
        r"(?:full\s+)?ingredients?\s*(?:list)?\s*[:\-]\s*(.{60,3000}?)"
        r"(?:$|(?:how\s+to\s+use)|(?:directions)|(?:key\s+ingredients))",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    candidate = match.group(1).strip()
    # An INCI list is comma-heavy. Prose about "key ingredients" is not.
    if candidate.count(",") < 4:
        return None
    return candidate


@dataclass(slots=True)
class ShopifyRetailer:
    """Config for one Shopify storefront."""

    key: str
    display_name: str
    domain: str
    currency: str = "USD"


class ShopifyScraper(RetailerScraper):
    requires_js = False

    def __init__(self, config: ShopifyRetailer) -> None:
        self.config = config
        self.key = config.key
        self.display_name = config.display_name
        self.currency = config.currency
        self.base_url = f"https://{config.domain}"

    async def search(self, query: str, limit: int = 10) -> list[SearchHit]:
        data = await fetch_json(
            f"{self.base_url}/search/suggest.json",
            params={
                "q": query,
                "resources[type]": "product",
                "resources[limit]": min(limit, 10),
            },
            headers={"Accept": "application/json"},
        )
        try:
            products = data["resources"]["results"]["products"]
        except (KeyError, TypeError):
            return []

        hits: list[SearchHit] = []
        for product in products:
            url = product.get("url") or ""
            handle = self._handle_from_url(url)
            if not handle:
                continue
            hits.append(
                SearchHit(
                    title=product.get("title") or "",
                    url=f"{self.base_url}/products/{handle}",
                    sku=handle,
                    price=parse_price(product.get("price")),
                    image_url=product.get("image"),
                )
            )
        return hits

    async def fetch_product(self, url: str) -> ScrapedProduct:
        handle = self._handle_from_url(url)
        if not handle:
            raise ScrapeFailed(f"cannot derive product handle from {url}")

        data = await fetch_json(
            f"{self.base_url}/products/{handle}.json",
            headers={"Accept": "application/json"},
        )
        product = data.get("product")
        if not product:
            raise ProductNotFound(url)

        variants = product.get("variants") or []
        if not variants:
            raise ScrapeFailed(f"no variants for {url}")
        variant = variants[0]

        price = parse_price(variant.get("price"))
        was_price = parse_price(variant.get("compare_at_price"))
        # Shopify sets compare_at_price even when it equals price; only a genuinely
        # higher value means the item is actually discounted.
        if was_price is not None and price is not None and was_price <= price:
            was_price = None

        body = html_to_text(product.get("body_html"))
        title = product.get("title") or ""
        # Size can live in the title, the variant title, or nowhere at all.
        size_value, size_unit = parse_size(title)
        if size_value is None:
            size_value, size_unit = parse_size(variant.get("title") or "")
        if size_value is None:
            size_value, size_unit = parse_size(body[:400])

        return ScrapedProduct(
            sku=handle,
            url=f"{self.base_url}/products/{handle}",
            title=title,
            brand=product.get("vendor"),
            price=price,
            was_price=was_price,
            currency=self.currency,
            in_stock=self._in_stock(variant),
            size_value=size_value,
            size_unit=size_unit,
            upc=self._clean_barcode(variant.get("barcode")),
            image_url=(product.get("image") or {}).get("src"),
            ingredients_raw=extract_ingredients(body),
            description=body[:2000] or None,
            extra={
                "product_type": product.get("product_type"),
                "tags": self._tags(product),
                "shopify_id": product.get("id"),
            },
        )

    async def list_catalog(self, page: int = 1, limit: int = 50) -> list[SearchHit]:
        """Walk the public catalog feed - used to discover products without search."""
        data = await fetch_json(
            f"{self.base_url}/products.json",
            params={"limit": min(limit, 250), "page": page},
            headers={"Accept": "application/json"},
        )
        hits = []
        for product in data.get("products", []):
            handle = product.get("handle")
            if not handle:
                continue
            variants = product.get("variants") or [{}]
            hits.append(
                SearchHit(
                    title=product.get("title") or "",
                    url=f"{self.base_url}/products/{handle}",
                    sku=handle,
                    price=parse_price(variants[0].get("price")),
                )
            )
        return hits

    @staticmethod
    def _tags(product: dict) -> list[str]:
        tags = product.get("tags")
        if isinstance(tags, list):
            return [str(t) for t in tags]
        if isinstance(tags, str):
            return [t.strip() for t in tags.split(",") if t.strip()]
        return []

    @staticmethod
    def _in_stock(variant: dict) -> bool:
        # `available` is absent from the .json endpoint; fall back to inventory
        # policy, which continues selling when set to "continue".
        available = variant.get("available")
        if isinstance(available, bool):
            return available
        quantity = variant.get("inventory_quantity")
        if isinstance(quantity, int) and quantity > 0:
            return True
        if variant.get("inventory_policy") == "continue":
            return True
        return quantity is None

    @staticmethod
    def _clean_barcode(barcode: str | None) -> str | None:
        if not barcode:
            return None
        digits = re.sub(r"\D", "", str(barcode))
        # Valid UPC-A / EAN-13 / EAN-8 lengths only; junk barcodes cause false matches.
        return digits if len(digits) in (8, 12, 13, 14) else None

    @staticmethod
    def _handle_from_url(url: str) -> str | None:
        match = re.search(r"/products/([^/?#]+)", url or "")
        return match.group(1) if match else None
