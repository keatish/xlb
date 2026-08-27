"""Quiz recommendations, routine building and conflict checking."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Concern, Product
from app.models.enums import CATEGORY_LABELS
from app.schemas import (
    ConcernOut,
    ConflictOut,
    ConflictRequest,
    QuizRequest,
    QuizResponse,
    Recommendation,
    RoutineOut,
)
from app.api.deps import build_analysis, latest_prices, product_query, to_summary
from app.services.analysis import detect_conflicts
from app.services.recommend import SkinProfile, build_routine, rank, score_product

router = APIRouter(prefix="/api", tags=["quiz"])


@router.get("/quiz/options")
async def quiz_options(session: AsyncSession = Depends(get_session)) -> dict:
    """Everything needed to render the quiz without hardcoding it in the frontend."""
    concerns = [
        ConcernOut(key=c.key, label=c.label, description=c.description)
        for c in (await session.execute(select(Concern).order_by(Concern.label))).scalars()
    ]
    return {
        "skin_types": [
            {"key": "dry", "label": "Dry", "description": "Tight, flaky, rarely shiny"},
            {"key": "oily", "label": "Oily", "description": "Shiny by midday, visible pores"},
            {"key": "combination", "label": "Combination", "description": "Oily T-zone, dry cheeks"},
            {"key": "normal", "label": "Normal", "description": "Balanced, rarely reactive"},
            {"key": "sensitive", "label": "Sensitive", "description": "Stings and reddens easily"},
        ],
        "concerns": [c.model_dump() for c in concerns],
        "categories": [{"key": k, "label": v} for k, v in CATEGORY_LABELS.items()],
        "budgets": [
            {"key": 15, "label": "Under $15"},
            {"key": 25, "label": "Under $25"},
            {"key": 40, "label": "Under $40"},
            {"key": 0, "label": "No limit"},
        ],
    }


@router.post("/quiz/recommend", response_model=QuizResponse)
async def recommend(
    payload: QuizRequest, session: AsyncSession = Depends(get_session)
) -> QuizResponse:
    stmt = product_query()
    if payload.categories:
        stmt = stmt.where(Product.category.in_(payload.categories))

    products = list((await session.execute(stmt)).scalars().unique())
    prices = await latest_prices(session, [p.id for p in products])

    concern_labels = {
        c.key: c.label
        for c in (await session.execute(select(Concern))).scalars()
    }

    profile = SkinProfile(
        skin_type=payload.skin_type,
        concerns=payload.concerns,
        sensitive=payload.sensitive or payload.skin_type == "sensitive",
        acne_prone=payload.acne_prone or "acne" in payload.concerns,
        fragrance_free=payload.fragrance_free,
        budget_max=payload.budget_max or None,
        categories=payload.categories,
    )

    summaries = {}
    analyses = {}
    scored = []
    for product in products:
        analysis = build_analysis(product)
        summary = to_summary(product, prices.get(product.id, []), analysis)
        analyses[product.id] = analysis
        summaries[product.id] = summary
        scored.append(
            score_product(
                product_id=product.id,
                analysis=analysis,
                profile=profile,
                price=summary.best_price,
                in_stock=any(p["in_stock"] for p in prices.get(product.id, [])) or not prices.get(product.id),
                concern_labels=concern_labels,
            )
        )

    top = rank(scored, limit=payload.limit)

    recommendations = [
        Recommendation(
            product=summaries[s.product_id],
            score=s.score,
            reasons=s.reasons,
            warnings=s.warnings,
        )
        for s in top
    ]

    # One product per category for the routine - a routine with three serums in
    # it is not a routine anyone can follow.
    best_per_category: dict[str, int] = {}
    for s in top:
        category = summaries[s.product_id].category
        best_per_category.setdefault(category, s.product_id)

    routine_ids = build_routine([(pid, cat) for cat, pid in best_per_category.items()])
    routine = RoutineOut(
        am=[summaries[i] for i in routine_ids["am"] if i in summaries],
        pm=[summaries[i] for i in routine_ids["pm"] if i in summaries],
    )

    conflicts = [
        ConflictOut(**c)
        for c in detect_conflicts(
            [(summaries[pid].name, analyses[pid]) for pid in best_per_category.values()]
        )
    ]

    return QuizResponse(recommendations=recommendations, routine=routine, conflicts=conflicts)


@router.post("/routine/conflicts", response_model=list[ConflictOut])
async def routine_conflicts(
    payload: ConflictRequest, session: AsyncSession = Depends(get_session)
) -> list[ConflictOut]:
    if not payload.product_ids:
        return []

    products = list(
        (
            await session.execute(product_query().where(Product.id.in_(payload.product_ids)))
        ).scalars().unique()
    )
    pairs = [(f"{p.brand.name} {p.name}" if p.brand else p.name, build_analysis(p)) for p in products]
    return [ConflictOut(**c) for c in detect_conflicts(pairs)]
