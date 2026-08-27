"""The retailer scraper contract.

Every retailer implements this interface, so adding retailer N+1 is one new file
plus a registry entry - nothing else in the system changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class ScrapeError(Exception):
    """Base for anything that went wrong fetching a page."""


class ScrapeBlocked(ScrapeError):
    """The retailer actively refused us - bot wall, 403, CAPTCHA.

    Deliberately distinct from ScrapeFailed: being blocked is a signal about the
    retailer that the scheduler acts on (back off, mark the source stale), not a
    bug in our parsing.
    """


class ScrapeFailed(ScrapeError):
    """Network error, timeout, or a page we could not parse."""


class ProductNotFound(ScrapeError):
    """The URL resolved but there is no product there any more."""


@dataclass(slots=True)
class SearchHit:
    """One result from a retailer search page."""

    title: str
    url: str
    sku: str
    price: float | None = None
    image_url: str | None = None


@dataclass(slots=True)
class ScrapedProduct:
    """Normalized product data. Every scraper returns this shape, whatever the
    source page looked like."""

    sku: str
    url: str
    title: str
    brand: str | None = None
    price: float | None = None
    was_price: float | None = None
    currency: str = "USD"
    in_stock: bool = True
    size_value: float | None = None
    size_unit: str | None = None
    upc: str | None = None
    image_url: str | None = None
    ingredients_raw: str | None = None
    description: str | None = None
    extra: dict = field(default_factory=dict)


class RetailerScraper(ABC):
    """Implement these two methods and the rest of the pipeline just works."""

    key: str
    display_name: str
    base_url: str
    currency: str = "USD"
    requires_js: bool = False

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[SearchHit]:
        """Find candidate listings for a free-text query."""

    @abstractmethod
    async def fetch_product(self, url: str) -> ScrapedProduct:
        """Fetch and parse one product page."""

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{type(self).__name__} key={self.key}>"
