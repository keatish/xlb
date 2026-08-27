"""Scheduled price refresh.

Reads from the DB, re-fetches each active listing and appends a new snapshot.
A retailer that blocks us is marked and skipped rather than retried into the
ground - the product page then shows a stale price with a timestamp instead of
an error.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Listing, PriceSnapshot, Retailer
from app.models.enums import ScrapeStatus
from app.scrapers.base import ScrapeBlocked, ScrapeError
from app.scrapers.registry import SCRAPERS
from app.scrapers.robots import RobotsDisallowed

logger = logging.getLogger(__name__)


async def refresh_listing(session, listing: Listing, scraper) -> bool:
    try:
        scraped = await scraper.fetch_product(listing.url)
    except RobotsDisallowed:
        listing.last_status = ScrapeStatus.BLOCKED
        logger.warning("robots.txt now disallows %s", listing.url)
        return False
    except ScrapeBlocked:
        listing.last_status = ScrapeStatus.BLOCKED
        return False
    except ScrapeError as exc:
        listing.last_status = ScrapeStatus.FAILED
        logger.warning("refresh failed for %s: %s", listing.url, exc)
        return False

    if scraped.price is None:
        listing.last_status = ScrapeStatus.FAILED
        return False

    session.add(
        PriceSnapshot(
            listing_id=listing.id,
            price=scraped.price,
            was_price=scraped.was_price,
            currency=scraped.currency,
            in_stock=scraped.in_stock,
            scraped_at=datetime.now(timezone.utc),
        )
    )
    listing.in_stock = scraped.in_stock
    listing.last_scraped_at = datetime.now(timezone.utc)
    listing.last_status = ScrapeStatus.OK
    return True


async def refresh_all_prices() -> dict[str, int]:
    settings = get_settings()
    stats = {"ok": 0, "failed": 0, "skipped": 0}
    semaphore = asyncio.Semaphore(settings.scrape_concurrency)

    async with SessionLocal() as session:
        retailers = {
            r.id: r for r in (await session.execute(select(Retailer))).scalars()
        }
        listings = list((await session.execute(select(Listing))).scalars())

        async def worker(listing: Listing) -> None:
            retailer = retailers.get(listing.retailer_id)
            scraper = SCRAPERS.get(retailer.scraper_key) if retailer else None
            if scraper is None or not retailer.is_active:
                stats["skipped"] += 1
                return
            async with semaphore:
                if await refresh_listing(session, listing, scraper):
                    stats["ok"] += 1
                else:
                    stats["failed"] += 1
                    if listing.last_status == ScrapeStatus.BLOCKED:
                        retailer.block_count += 1

        await asyncio.gather(*(worker(listing) for listing in listings))
        await session.commit()

    logger.info("price refresh: %s", stats)
    return stats


def start_scheduler() -> AsyncIOScheduler:
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        refresh_all_prices,
        "interval",
        hours=settings.refresh_interval_hours,
        id="refresh_prices",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    return scheduler
