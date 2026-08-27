"""Product search, detail, price history and dupes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import Brand, Concern, Product, ProductConcern
from app.models.enums import CATEGORY_LABELS
from app.schemas import (
    BrandOut,
    ConcernOut,
    DupeOut,
    FilterOptions,
    PriceHistory,
    ProductDetail,
    ProductPage,
    ProductSummary,
)
from app.api.deps import (
    build_analysis,
    latest_prices,
    price_history,
    product_query,
    to_detail,
    to_summary,
)
from app.services.dupes import find_dupes

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=ProductPage)
async def list_products(
    q: str | None = Query(None, description="free-text search over brand and name"),
    category: str | None = None,
    concern: str | None = None,
    brand: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    sort: str = Query("relevance", pattern="^(relevance|price_asc|price_desc|name)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> ProductPage:
    stmt = product_query().join(Brand, Brand.id == Product.brand_id)

    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(Product.name.ilike(pattern), Brand.name.ilike(pattern)))
    if category:
        stmt = stmt.where(Product.category == category)
    if brand:
        stmt = stmt.where(Brand.slug == brand)
    if concern:
        stmt = stmt.where(
            Product.id.in_(
                select(ProductConcern.product_id)
                .join(Concern, Concern.id == ProductConcern.concern_id)
                .where(Concern.key == concern)
            )
        )

    if sort == "name":
        stmt = stmt.order_by(Brand.name, Product.name)
    else:
        stmt = stmt.order_by(Product.id)

    products = list((await session.execute(stmt)).scalars().unique())

    prices = await latest_prices(session, [p.id for p in products])
    summaries: list[ProductSummary] = []
    for product in products:
        summary = to_summary(product, prices.get(product.id, []), build_analysis(product))
        # Price filters apply to the best available price, which is what a user
        # comparing prices actually cares about.
        if min_price is not None and (summary.best_price is None or summary.best_price < min_price):
            continue
        if max_price is not None and (summary.best_price is None or summary.best_price > max_price):
            continue
        summaries.append(summary)

    if sort == "price_asc":
        summaries.sort(key=lambda s: (s.best_price is None, s.best_price or 0))
    elif sort == "price_desc":
        summaries.sort(key=lambda s: (s.best_price is None, -(s.best_price or 0)))

    total = len(summaries)
    start = (page - 1) * page_size
    return ProductPage(
        items=summaries[start : start + page_size],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/filters", response_model=FilterOptions)
async def filter_options(session: AsyncSession = Depends(get_session)) -> FilterOptions:
    """Everything the filter sidebar needs, in one request."""
    products = list((await session.execute(product_query())).scalars().unique())

    # Counts come from the visible set, not from a COUNT(*) over the table: a
    # sidebar that advertises 12 cleansers and then lists 3 is worse than no count.
    counts: dict[str, int] = {}
    for product in products:
        key = getattr(product.category, "value", product.category)
        counts[key] = counts.get(key, 0) + 1

    categories = [
        {"key": key, "label": label, "count": counts[key]}
        for key, label in CATEGORY_LABELS.items()
        if counts.get(key)
    ]

    concerns = [
        ConcernOut(key=c.key, label=c.label, description=c.description)
        for c in (await session.execute(select(Concern).order_by(Concern.label))).scalars()
    ]

    # Only offer brands that have a product the catalog will actually show.
    # Listing a brand whose every product is hidden gives the user a filter that
    # returns nothing.
    visible_brand_ids = {p.brand_id for p in products}
    brands = [
        BrandOut(id=b.id, name=b.name, slug=b.slug)
        for b in (await session.execute(select(Brand).order_by(Brand.name))).scalars()
        if b.id in visible_brand_ids
    ]

    prices = await latest_prices(session, [p.id for p in products])
    best = [
        s.best_price
        for s in (to_summary(p, prices.get(p.id, [])) for p in products)
        if s.best_price is not None
    ]

    return FilterOptions(
        categories=categories,
        concerns=concerns,
        brands=brands,
        price_range={
            "min": round(min(best), 2) if best else 0,
            "max": round(max(best), 2) if best else 0,
        },
    )


@router.get("/deals", response_model=list[ProductSummary])
async def deals(
    limit: int = Query(8, ge=1, le=40),
    session: AsyncSession = Depends(get_session),
) -> list[ProductSummary]:
    """Products with the biggest gap between the cheapest and dearest retailer.

    This is the clearest demonstration of why the site exists: same product,
    very different prices.
    """
    products = list((await session.execute(product_query())).scalars().unique())
    prices = await latest_prices(session, [p.id for p in products])

    summaries = [
        to_summary(p, prices.get(p.id, []), build_analysis(p)) for p in products
    ]
    comparable = [
        s for s in summaries
        if s.best_price is not None and s.highest_price is not None and s.retailer_count > 1
    ]
    comparable.sort(key=lambda s: -(s.highest_price - s.best_price))
    return comparable[:limit]


@router.get("/{slug}", response_model=ProductDetail)
async def product_detail(
    slug: str, session: AsyncSession = Depends(get_session)
) -> ProductDetail:
    product = (
        await session.execute(product_query().where(Product.slug == slug))
    ).scalars().unique().one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")

    prices = (await latest_prices(session, [product.id])).get(product.id, [])
    detail = to_detail(product, prices, build_analysis(product))

    history = await price_history(session, product.id, days=90)
    points = [p.price for series in history for p in series.points]
    if points:
        detail.lowest_90d = round(min(points), 2)
        detail.highest_90d = round(max(points), 2)

    return detail


@router.get("/{slug}/prices", response_model=list[PriceHistory])
async def product_prices(
    slug: str,
    days: int = Query(90, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
) -> list[PriceHistory]:
    product = (
        await session.execute(select(Product).where(Product.slug == slug))
    ).scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    return await price_history(session, product.id, days=days)


@router.get("/{slug}/dupes", response_model=list[DupeOut])
async def product_dupes(
    slug: str,
    limit: int = Query(8, ge=1, le=20),
    cheaper_only: bool = True,
    session: AsyncSession = Depends(get_session),
) -> list[DupeOut]:
    target = (
        await session.execute(product_query().where(Product.slug == slug))
    ).scalars().unique().one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="product not found")

    same_category = list(
        (
            await session.execute(
                product_query().where(Product.category == target.category)
            )
        ).scalars().unique()
    )

    prices = await latest_prices(session, [p.id for p in same_category])
    summaries = {
        p.id: to_summary(p, prices.get(p.id, []), build_analysis(p)) for p in same_category
    }
    analyses = {p.id: build_analysis(p) for p in same_category}

    target_category = (
        target.category.value if hasattr(target.category, "value") else str(target.category)
    )
    candidates = [
        (p.id, analyses[p.id], summaries[p.id].best_price, target_category)
        for p in same_category
    ]

    results = find_dupes(
        target_id=target.id,
        target=analyses[target.id],
        target_price=summaries[target.id].best_price,
        target_category=target_category,
        candidates=candidates,
        limit=limit,
        cheaper_only=cheaper_only,
    )

    return [
        DupeOut(
            product=summaries[d.product_id],
            similarity=d.similarity,
            shared_actives=d.shared_actives,
            savings=d.savings,
        )
        for d in results
        if d.product_id in summaries
    ]
