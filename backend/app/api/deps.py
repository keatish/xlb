"""Shared query helpers for the API routers.

Loading a product means loading its brand, ingredients and current prices
together - doing that in one place keeps the N+1 queries out of the routers.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models import (
    Brand,
    Listing,
    PriceSnapshot,
    Product,
    ProductConcern,
    ProductIngredient,
    Retailer,
)
from app.schemas import (
    IngredientOut,
    PricePoint,
    PriceHistory,
    ProductAnalysis,
    ProductDetail,
    ProductSummary,
    RetailerPrice,
)
from app.services.analysis import Analysis, analyze

# A listing that has not been refreshed in this long is shown with a staleness
# warning rather than hidden - a stale price beats no price, as long as we say so.
STALE_AFTER = timedelta(hours=36)


def product_query() -> Select:
    # The nested selectinload matters: without it, reading link.ingredient later
    # triggers a lazy load outside the async context and raises MissingGreenlet.
    return select(Product).options(
        selectinload(Product.brand),
        selectinload(Product.ingredients).selectinload(ProductIngredient.ingredient),
        selectinload(Product.concerns).selectinload(ProductConcern.concern),
    )


async def latest_prices(
    session: AsyncSession, product_ids: list[int]
) -> dict[int, list[dict]]:
    """Most recent snapshot per listing, grouped by product.

    Listings flagged needs_review are excluded: a low-confidence match means we
    are not sure it is the same product, and a wrong price is worse than none.
    """
    if not product_ids:
        return {}

    settings = get_settings()

    newest = (
        select(
            PriceSnapshot.listing_id.label("listing_id"),
            func.max(PriceSnapshot.scraped_at).label("newest"),
        )
        .group_by(PriceSnapshot.listing_id)
        .subquery()
    )

    stmt = (
        select(Listing, Retailer, PriceSnapshot)
        .join(Retailer, Retailer.id == Listing.retailer_id)
        .join(newest, newest.c.listing_id == Listing.id)
        .join(
            PriceSnapshot,
            (PriceSnapshot.listing_id == Listing.id)
            & (PriceSnapshot.scraped_at == newest.c.newest),
        )
        .where(
            Listing.product_id.in_(product_ids),
            Listing.needs_review.is_(False),
            Listing.match_confidence >= settings.match_confidence_threshold,
        )
    )

    now = datetime.now(timezone.utc)
    grouped: dict[int, list[dict]] = {}
    for listing, retailer, snapshot in (await session.execute(stmt)).all():
        scraped = listing.last_scraped_at or snapshot.scraped_at
        if scraped is not None and scraped.tzinfo is None:
            scraped = scraped.replace(tzinfo=timezone.utc)
        grouped.setdefault(listing.product_id, []).append(
            {
                "retailer": retailer.name,
                "retailer_slug": retailer.slug,
                "url": listing.url,
                "price": float(snapshot.price) if snapshot.price is not None else None,
                "was_price": float(snapshot.was_price) if snapshot.was_price else None,
                "currency": snapshot.currency,
                "in_stock": snapshot.in_stock,
                "last_scraped_at": scraped,
                "is_stale": bool(scraped and (now - scraped) > STALE_AFTER),
            }
        )

    for rows in grouped.values():
        priced = [r for r in rows if r["price"] is not None and r["in_stock"]]
        if priced:
            best = min(priced, key=lambda r: r["price"])
            best["is_best"] = True
        rows.sort(key=lambda r: (r["price"] is None, r["price"] or 0))

    return grouped


def build_analysis(product: Product) -> Analysis:
    names = [link.ingredient.inci_name for link in sorted(
        product.ingredients, key=lambda link: link.position
    )]
    return analyze(names)


def to_summary(product: Product, prices: list[dict], analysis: Analysis | None = None) -> ProductSummary:
    priced = [p["price"] for p in prices if p["price"] is not None]
    actives: list[str] = []
    if analysis:
        seen: set[str] = set()
        for ingredient in analysis.actives:
            label = ingredient.common_name or ingredient.inci_name
            if label in seen:
                continue
            seen.add(label)
            actives.append(label)
            if len(actives) >= 4:
                break

    return ProductSummary(
        id=product.id,
        slug=product.slug,
        name=product.name,
        brand=product.brand.name if product.brand else "",
        category=product.category.value if hasattr(product.category, "value") else str(product.category),
        size_label=product.size_label,
        image_url=product.image_url,
        best_price=min(priced) if priced else None,
        highest_price=max(priced) if priced else None,
        retailer_count=len(prices),
        on_sale=any(p.get("was_price") for p in prices),
        concerns=[link.concern.key for link in product.concerns if link.concern],
        key_actives=actives,
    )


def to_detail(product: Product, prices: list[dict], analysis: Analysis) -> ProductDetail:
    summary = to_summary(product, prices, analysis)
    ingredients = [
        IngredientOut(
            position=i.position,
            inci_name=i.inci_name,
            common_name=i.common_name,
            function=i.function,
            is_active=i.is_active,
            is_irritant=i.is_irritant,
            comedogenic_rating=i.comedogenic_rating,
            active_group=i.active_group,
            description=i.description,
            known=i.known,
            is_prominent=i.is_prominent,
        )
        for i in analysis.ingredients
    ]

    return ProductDetail(
        **summary.model_dump(),
        description=product.description,
        upc=product.upc,
        ingredients=ingredients,
        analysis=ProductAnalysis(
            active_groups=sorted(analysis.active_groups),
            max_comedogenic=analysis.max_comedogenic,
            has_fragrance=analysis.has_fragrance,
            has_alcohol=analysis.has_alcohol,
            has_essential_oil=analysis.has_essential_oil,
            known_count=analysis.known_count,
            unknown_count=analysis.unknown_count,
        ),
        prices=[RetailerPrice(**p) for p in prices],
    )


async def price_history(
    session: AsyncSession, product_id: int, days: int = 90
) -> list[PriceHistory]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(Retailer.name, Retailer.slug, PriceSnapshot.scraped_at, PriceSnapshot.price)
        .join(Listing, Listing.retailer_id == Retailer.id)
        .join(PriceSnapshot, PriceSnapshot.listing_id == Listing.id)
        .where(
            Listing.product_id == product_id,
            Listing.needs_review.is_(False),
            PriceSnapshot.scraped_at >= since,
        )
        .order_by(PriceSnapshot.scraped_at)
    )

    series: dict[str, PriceHistory] = {}
    for name, slug, scraped_at, price in (await session.execute(stmt)).all():
        entry = series.get(slug)
        if entry is None:
            entry = PriceHistory(retailer=name, retailer_slug=slug, points=[])
            series[slug] = entry
        entry.points.append(PricePoint(date=scraped_at, price=float(price)))

    return list(series.values())


async def brand_lookup(session: AsyncSession) -> dict[int, Brand]:
    return {b.id: b for b in (await session.execute(select(Brand))).scalars()}
