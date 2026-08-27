"""Ingest live products from real retailers into the catalog.

The counterpart to jobs/seed.py: where seed.py invents a catalog, this one
discovers real SKUs, real prices and real product images from retailers we are
allowed to crawl, and writes them into the same schema.

    python -m app.jobs.ingest --limit 10
    python -m app.jobs.ingest --limit 10 --dry-run
    python -m app.jobs.ingest --limit 10 --no-ingredients

Pipeline per product:

  1. Discover  - walk the retailer's public catalog feed, keep in-scope skincare.
  2. Fetch     - full product record (barcode, image, description) per handle.
  3. Enrich    - INCI list from INCIDecoder, which retailers do not publish.
  4. Match     - look for the same SKU at a second retailer so there is a price
                 to compare. Barcode first, gated fuzzy second.
  5. Persist   - brand, product, ingredient links, concern weights, listings and
                 one price snapshot each.

Idempotent: re-running matches existing products on barcode then slug, so it
appends a fresh price snapshot instead of duplicating the catalog.

Every request goes through scrapers/fetch.py, so robots.txt is enforced and
per-domain throttling applies. Nothing here bypasses that.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime, timezone

from slugify import slugify
from sqlalchemy import select

from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.models import (
    Brand,
    Concern,
    Ingredient,
    Listing,
    PriceSnapshot,
    Product,
    ProductConcern,
    ProductIngredient,
    Retailer,
)
from app.models.enums import MatchMethod, ScrapeStatus
from app.scrapers import incidecoder
from app.scrapers.base import ScrapedProduct, ScrapeError
from app.scrapers.fetch import fetch_json
from app.scrapers.registry import get_scraper
from app.scrapers.robots import RobotsDisallowed
from app.services.analysis import Analysis, analyze, config
from app.services.inci import (
    canonicalize,
    lookup,
    normalize_name_list,
    parse_ingredients,
)
from app.services.matching import build_candidate, classify_category, compare
from app.services.text import clean_product_name, normalize_text

logger = logging.getLogger(__name__)

# Where canonical products come from, and where we look for a second price.
PRIMARY_RETAILER = "sokoglam"
COMPARE_RETAILER = "ohlolly"

# classify_category() is a classifier, not a gatekeeper: it falls back to
# TREATMENT for anything it does not recognise, which silently turns a hair brush
# into a skincare treatment. Scope has to be decided before classification.
#
# README scope: skincare only. Makeup, haircare, fragrance and tools are out.
OUT_OF_SCOPE_TYPES = {
    "skincare set", "gift set", "set", "kit", "tools", "tool", "device",
    "hair brush", "hair treatment", "hair care", "haircare", "shampoo",
    "conditioner", "body care", "bodycare", "fragrance", "perfume",
    "lip color", "lipstick", "lip tint", "makeup", "makeup remover",
    "bb/cc cream", "cushion", "foundation", "concealer", "mascara",
    "eyeshadow", "blush", "brow", "eyeliner", "nail", "supplement",
    "accessories", "apparel", "candle", "book",
}

# Title markers that mean "not a single skincare SKU" even when product_type is
# blank or misleading. A set has no one INCI list, size or barcode, so it cannot
# be a canonical product in this schema.
OUT_OF_SCOPE_MARKERS = (
    " set ", " set(", "set (", "bundle", " kit", " duo", " trio",
    "gift", "sampler", "discovery", "brush", "headband", "hair ",
    "shampoo", "conditioner", "lip balm", "lip oil", "lip tint",
    "body wash", "body lotion", "hand cream", "foot ", "device",
    "led ", "roller", "gua sha", "tweezer", "spatula", "e-gift",
)


def is_in_scope(product_type: str | None, title: str, tags: list[str] | None = None) -> bool:
    """Is this a single skincare SKU we can model as one canonical product?"""
    ptype = (product_type or "").strip().lower()
    if ptype in OUT_OF_SCOPE_TYPES:
        return False

    lowered = f" {(title or '').lower()} "
    if any(marker in lowered for marker in OUT_OF_SCOPE_MARKERS):
        return False
    if lowered.rstrip().endswith(" set"):
        return False

    tag_text = " ".join(tags or []).lower()
    for word in ("gift set", "hair", "makeup", "fragrance", "tools"):
        if word in tag_text and "skincare" not in tag_text:
            return False

    return True


async def raw_feed(scraper, page: int, limit: int) -> list[dict]:
    """Raw catalog feed.

    list_catalog() drops product_type and images, which the scope filter and the
    image requirement both need, so this reads the feed directly.
    """
    data = await fetch_json(
        f"{scraper.base_url}/products.json",
        params={"limit": min(limit, 250), "page": page},
        headers={"Accept": "application/json"},
    )
    return data.get("products", [])


async def discover(scraper, want: int, max_pages: int = 6) -> list[str]:
    """Page the catalog feed until we have `want` in-scope handles."""
    handles: list[str] = []
    seen: set[str] = set()

    for page in range(1, max_pages + 1):
        products = await raw_feed(scraper, page=page, limit=250)
        if not products:
            break

        for product in products:
            handle = product.get("handle")
            if not handle or handle in seen:
                continue
            seen.add(handle)

            title = product.get("title") or ""
            tags = scraper._tags(product)
            if not is_in_scope(product.get("product_type"), title, tags):
                continue

            # No image means nothing to show in the UI, which is half the point.
            images = product.get("images") or []
            if not images or not (images[0] or {}).get("src"):
                logger.debug("skipping %s: no image", handle)
                continue

            handles.append(handle)
            if len(handles) >= want:
                return handles

    return handles


async def ensure_retailer(session, scraper) -> Retailer:
    existing = (
        await session.execute(select(Retailer).where(Retailer.scraper_key == scraper.key))
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    retailer = Retailer(
        name=scraper.display_name,
        slug=scraper.key,
        base_url=scraper.base_url,
        scraper_key=scraper.key,
        is_active=True,
    )
    session.add(retailer)
    await session.flush()
    logger.info("created retailer %s", retailer.slug)
    return retailer


async def ensure_reference_data(session) -> tuple[dict[str, Ingredient], dict[str, Concern]]:
    """Ingredient dictionary and concern rows are reference data, not synthetic
    data, so the seed module's idempotent helpers are the right thing to reuse."""
    from app.jobs.seed import seed_concerns, seed_ingredients

    ingredients = await seed_ingredients(session)
    concerns = await seed_concerns(session)
    return ingredients, concerns


async def ensure_brand(session, name: str | None, cache: dict[str, Brand]) -> Brand:
    brand_name = (name or "Unknown").strip() or "Unknown"
    if brand_name in cache:
        return cache[brand_name]

    existing = (
        await session.execute(select(Brand).where(Brand.name == brand_name))
    ).scalar_one_or_none()
    if existing is None:
        existing = Brand(
            name=brand_name,
            slug=slugify(brand_name) or slugify(f"brand-{brand_name}"),
            normalized_name=brand_name.lower(),
        )
        session.add(existing)
        await session.flush()

    cache[brand_name] = existing
    return existing


async def ensure_ingredient(session, inci_name: str, cache: dict[str, Ingredient]) -> Ingredient:
    """Get or create one Ingredient row, keyed on the canonical INCI name.

    Canonicalizing first is what keeps this idempotent: the dictionary maps many
    raw spellings onto one name, so looking up and inserting under the *raw*
    string collides with the row that already exists under the canonical one.

    Live INCI lists routinely contain names our dictionary has never heard of.
    Those still get a row: the product page renders the full list from these
    links, and analyze() marks unknowns rather than choking on them. Known names
    are enriched from the dictionary exactly as seed.py does.
    """
    entry = lookup(inci_name) or {}
    canonical = entry.get("inci_name") or canonicalize(inci_name) or inci_name.strip()
    canonical = canonical[:120]
    key = normalize_text(canonical)
    if not key:
        raise ValueError(f"empty ingredient name from {inci_name!r}")
    if key in cache:
        return cache[key]

    existing = (
        await session.execute(select(Ingredient).where(Ingredient.inci_name == canonical))
    ).scalar_one_or_none()

    if existing is None:
        base_slug = (slugify(canonical) or key.replace(" ", "-"))[:120]
        slug = base_slug
        # Distinct INCI names can normalize to the same slug; keep them apart.
        suffix = 2
        while (
            await session.execute(select(Ingredient).where(Ingredient.slug == slug))
        ).scalar_one_or_none() is not None:
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        existing = Ingredient(
            inci_name=canonical,
            slug=slug,
            common_name=entry.get("common_name"),
            function=entry.get("function"),
            is_active=bool(entry.get("is_active")),
            is_irritant=bool(entry.get("is_irritant")),
            comedogenic_rating=entry.get("comedogenic_rating"),
            active_group=entry.get("active_group"),
            description=entry.get("description"),
        )
        session.add(existing)
        await session.flush()

    cache[key] = existing
    return existing


def derive_concerns(analysis: Analysis) -> dict[str, float]:
    """Concern weights implied by the ingredient list.

    Uses the same concern_ingredients table the recommender scores against, so a
    live product answers the quiz on the same basis as a seeded one instead of
    being invisible to it.
    """
    weights: dict[str, float] = {}
    for concern_key, entries in config()["concern_ingredients"].items():
        best = 0.0
        for entry in entries:
            if "group" in entry:
                value = analysis.group_weight(entry["group"]) * entry.get("weight", 1.0)
            elif "inci" in entry:
                value = analysis.ingredient_weight(entry["inci"]) * entry.get("weight", 1.0)
            else:
                continue
            best = max(best, value)
        if best > 0:
            weights[concern_key] = round(min(best, 1.0), 3)
    return weights


async def find_existing_product(session, scraped: ScrapedProduct, slug: str) -> Product | None:
    """Barcode is definitive; slug catches re-runs of barcode-less products."""
    if scraped.upc:
        found = (
            await session.execute(select(Product).where(Product.upc == scraped.upc))
        ).scalar_one_or_none()
        if found is not None:
            return found
    return (
        await session.execute(select(Product).where(Product.slug == slug))
    ).scalar_one_or_none()


async def attach_ingredients(session, product: Product, names: list[str], cache) -> int:
    """Replace this product's ingredient links with `names`, in order."""
    existing = (
        (
            await session.execute(
                select(ProductIngredient).where(ProductIngredient.product_id == product.id)
            )
        )
        .scalars()
        .all()
    )
    for link in existing:
        await session.delete(link)
    await session.flush()

    seen: set[int] = set()
    position = 0
    for raw in names:
        name = raw.strip()
        if not name:
            continue
        try:
            ingredient = await ensure_ingredient(session, name, cache)
        except ValueError:
            continue
        # Two raw spellings can canonicalize to the same ingredient row.
        if ingredient.id in seen:
            continue
        seen.add(ingredient.id)
        position += 1
        session.add(
            ProductIngredient(
                product_id=product.id,
                ingredient_id=ingredient.id,
                position=position,
            )
        )
    await session.flush()
    return position


async def attach_concerns(session, product: Product, weights: dict[str, float], concerns) -> int:
    existing = (
        (
            await session.execute(
                select(ProductConcern).where(ProductConcern.product_id == product.id)
            )
        )
        .scalars()
        .all()
    )
    for link in existing:
        await session.delete(link)
    await session.flush()

    count = 0
    for key, weight in weights.items():
        concern = concerns.get(key)
        if concern is None:
            continue
        session.add(
            ProductConcern(product_id=product.id, concern_id=concern.id, weight=weight)
        )
        count += 1
    await session.flush()
    return count


async def upsert_listing(
    session,
    product: Product,
    retailer: Retailer,
    scraped: ScrapedProduct,
    confidence: float,
    method: MatchMethod,
    threshold: float,
) -> tuple[Listing, bool]:
    """Create or update the listing, then append a price snapshot."""
    listing = (
        await session.execute(
            select(Listing).where(
                Listing.retailer_id == retailer.id,
                Listing.retailer_sku == scraped.sku,
            )
        )
    ).scalar_one_or_none()

    created = listing is None
    now = datetime.now(timezone.utc)

    if listing is None:
        listing = Listing(
            product_id=product.id,
            retailer_id=retailer.id,
            retailer_sku=scraped.sku,
            url=scraped.url[:900],
            title_raw=scraped.title[:400],
        )
        session.add(listing)

    listing.product_id = product.id
    listing.url = scraped.url[:900]
    listing.title_raw = scraped.title[:400]
    listing.in_stock = scraped.in_stock
    listing.last_scraped_at = now
    listing.last_status = ScrapeStatus.OK
    listing.match_confidence = confidence
    listing.match_method = method
    listing.needs_review = confidence < threshold
    await session.flush()

    if scraped.price is not None:
        session.add(
            PriceSnapshot(
                listing_id=listing.id,
                price=scraped.price,
                was_price=scraped.was_price,
                currency=scraped.currency,
                in_stock=scraped.in_stock,
                scraped_at=now,
            )
        )
        await session.flush()

    return listing, created


async def find_at_compare_retailer(scraper, scraped: ScrapedProduct, threshold: float):
    """Search the second retailer for the same SKU.

    Returns (ScrapedProduct, MatchResult) or (None, None). A miss is normal - two
    retailers rarely carry identical ranges - so it never raises.
    """
    query = clean_product_name(scraped.title, scraped.brand) or scraped.title
    if scraped.brand:
        query = f"{scraped.brand} {query}".strip()

    try:
        hits = await scraper.search(query, limit=5)
    except (ScrapeError, RobotsDisallowed) as exc:
        logger.info("compare search failed for %r: %s", query, exc)
        return None, None

    target = build_candidate(
        scraped.brand, scraped.title, scraped.size_value, scraped.size_unit, scraped.upc
    )

    best = None
    best_result = None
    for hit in hits:
        try:
            other = await scraper.fetch_product(hit.url)
        except (ScrapeError, RobotsDisallowed):
            continue

        result = compare(
            target,
            build_candidate(
                other.brand, other.title, other.size_value, other.size_unit, other.upc
            ),
            threshold=threshold,
        )
        if best_result is None or result.confidence > best_result.confidence:
            best, best_result = other, result
        if result.method is MatchMethod.UPC and result.matched:
            break

    if best_result is None or not best_result.matched:
        return None, None
    return best, best_result


async def ingest(limit: int, with_ingredients: bool, dry_run: bool, compare_prices: bool) -> dict:
    settings = get_settings()
    threshold = settings.match_confidence_threshold

    primary = get_scraper(PRIMARY_RETAILER)
    secondary = get_scraper(COMPARE_RETAILER) if compare_prices else None

    stats = {
        "discovered": 0,
        "products_created": 0,
        "products_updated": 0,
        "listings_created": 0,
        "compare_listings": 0,
        "with_ingredients": 0,
        "snapshots": 0,
        "skipped": 0,
    }

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    logger.info("discovering up to %s in-scope products from %s", limit, primary.key)
    handles = await discover(primary, want=limit)
    stats["discovered"] = len(handles)
    logger.info("discovered %s handles", len(handles))
    if not handles:
        return stats

    async with SessionLocal() as session:
        ingredient_rows, concerns = await ensure_reference_data(session)
        cache = {normalize_text(name): row for name, row in ingredient_rows.items()}
        retailer = await ensure_retailer(session, primary)
        compare_retailer = await ensure_retailer(session, secondary) if secondary else None
        brands: dict[str, Brand] = {}
        await session.commit()

        for index, handle in enumerate(handles, start=1):
            url = f"{primary.base_url}/products/{handle}"
            try:
                scraped = await primary.fetch_product(url)
            except (ScrapeError, RobotsDisallowed) as exc:
                logger.warning("[%s/%s] %s: %s", index, len(handles), handle, exc)
                stats["skipped"] += 1
                continue

            if scraped.price is None:
                logger.warning("[%s/%s] %s: no price, skipping", index, len(handles), handle)
                stats["skipped"] += 1
                continue

            names: list[str] = []
            source_slug = None
            if with_ingredients:
                try:
                    names, source_slug = await incidecoder.find_ingredients_for(
                        scraped.brand, clean_product_name(scraped.title, scraped.brand)
                    )
                except Exception as exc:  # noqa: BLE001 - enrichment is optional
                    logger.info("incidecoder lookup failed for %s: %s", handle, exc)
                # INCIDecoder gives pre-split names; canonicalize and dedupe them.
                names = normalize_name_list(names)
            if not names and scraped.ingredients_raw:
                names = parse_ingredients(scraped.ingredients_raw)

            brand = await ensure_brand(session, scraped.brand, brands)
            clean_name = clean_product_name(scraped.title, scraped.brand) or scraped.title
            display_name = scraped.title.strip() or clean_name
            slug = slugify(f"{brand.name} {display_name}")[:340]

            product = await find_existing_product(session, scraped, slug)
            created = product is None
            if product is None:
                product = Product(brand_id=brand.id, name=display_name[:300], slug=slug)
                session.add(product)

            product.brand_id = brand.id
            product.name = display_name[:300]
            product.category = classify_category(
                scraped.extra.get("product_type"), scraped.title, scraped.extra.get("tags")
            )
            product.size_value = scraped.size_value
            product.size_unit = scraped.size_unit
            product.upc = scraped.upc
            product.description = scraped.description
            if scraped.image_url:
                product.image_url = scraped.image_url[:600]
            if names:
                product.ingredients_raw = ", ".join(names)
            await session.flush()

            if created:
                stats["products_created"] += 1
            else:
                stats["products_updated"] += 1

            linked = 0
            concern_count = 0
            if names:
                linked = await attach_ingredients(session, product, names, cache)
                analysis = analyze(list(names))
                concern_count = await attach_concerns(
                    session, product, derive_concerns(analysis), concerns
                )
                stats["with_ingredients"] += 1

            _, listing_created = await upsert_listing(
                session,
                product,
                retailer,
                scraped,
                confidence=1.0,
                method=MatchMethod.UPC if scraped.upc else MatchMethod.MANUAL,
                threshold=threshold,
            )
            if listing_created:
                stats["listings_created"] += 1
            stats["snapshots"] += 1

            logger.info(
                "[%s/%s] %s %s | %s | $%s | img=%s upc=%s inci=%s concerns=%s%s",
                index,
                len(handles),
                "NEW" if created else "UPD",
                display_name[:42],
                product.category.value,
                scraped.price,
                "Y" if product.image_url else "N",
                scraped.upc or "-",
                linked,
                concern_count,
                f" (incidecoder:{source_slug})" if source_slug else "",
            )

            if secondary is not None and compare_retailer is not None:
                other, result = await find_at_compare_retailer(secondary, scraped, threshold)
                if other is not None and result is not None:
                    _, second_created = await upsert_listing(
                        session,
                        product,
                        compare_retailer,
                        other,
                        confidence=result.confidence,
                        method=result.method,
                        threshold=threshold,
                    )
                    if second_created:
                        stats["compare_listings"] += 1
                    if other.price is not None:
                        stats["snapshots"] += 1
                    logger.info(
                        "        also at %s: $%s (%s %.2f)",
                        compare_retailer.slug,
                        other.price,
                        result.method.value,
                        result.confidence,
                    )

        if dry_run:
            await session.rollback()
            logger.info("dry run - rolled back, nothing written")
        else:
            await session.commit()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest live products into the catalog.")
    parser.add_argument("--limit", type=int, default=10, help="how many products to ingest")
    parser.add_argument("--dry-run", action="store_true", help="fetch and report, write nothing")
    parser.add_argument(
        "--no-ingredients", action="store_true", help="skip the INCIDecoder lookup"
    )
    parser.add_argument(
        "--no-compare",
        action="store_true",
        help=f"do not look for a second price at {COMPARE_RETAILER}",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    stats = asyncio.run(
        ingest(
            limit=args.limit,
            with_ingredients=not args.no_ingredients,
            dry_run=args.dry_run,
            compare_prices=not args.no_compare,
        )
    )
    print("\ningest complete:")
    for key, value in stats.items():
        print(f"  {key:20} {value}")


if __name__ == "__main__":
    main()
