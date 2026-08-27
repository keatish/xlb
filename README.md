# xlb — Skincare Price Comparison & Recommendation

A skincare website that does three things:

1. **Describes products** — full INCI ingredient lists with active/irritant analysis
2. **Compares prices** for the same product across multiple retailers
3. **Recommends products** from a skin-type and skin-concern quiz

Scope is skincare only — cleansers, toners, essences, serums, moisturizers,
sunscreens, masks, eye creams, exfoliants and treatments. Makeup, haircare and
fragrance are deliberately out of scope: they need a different attribute model
(shade, finish, coverage) and none of the ingredient-driven features here
transfer to them.

## Stack

| Layer | Choice |
|---|---|
| Frontend | React 18 + TypeScript + Vite + Material UI |
| Backend | FastAPI + SQLAlchemy 2.0 (async) + Alembic |
| Database | SQLite by default, Postgres via `DATABASE_URL` |
| Scraping | httpx + selectolax, robots.txt enforced |
| Matching | rapidfuzz, gated on barcode and size |

## Quick start

```bash
# Backend
cd backend
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"   # Windows
# source .venv/bin/activate && pip install -e ".[dev]" # macOS/Linux

python -m app.jobs.seed --reset  # creates tables + synthetic seed data
python -m pytest                 # 55 tests
python -m uvicorn app.main:app --reload   # http://localhost:8000/docs
```

The schema is currently created with SQLAlchemy `create_all` on startup. Alembic
is declared as a dependency but migrations are not wired up yet — that is the
next thing to do before this touches a database anyone cares about.

```bash
# Frontend
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

Postgres instead of SQLite:

```bash
docker compose up -d
export DATABASE_URL=postgresql+asyncpg://xlb:xlb@localhost:5432/xlb
```

## How price comparison works

A `product` is the canonical SKU. A `listing` is that product at one retailer. A
`price_snapshot` is an append-only observation of a listing's price, which is what
makes the history chart and "lowest in 90 days" possible.

Matching a listing to a canonical product runs in this order:

1. **Barcode.** Identical GTIN means identical SKU — confidence 1.0.
2. **Fuzzy.** Normalized brand + name similarity, gated on size and pack count.
3. **Below threshold** (default 0.85) the listing is stored but flagged
   `needs_review` and hidden from the public price table.

That last rule is deliberate: showing a wrong price is worse than showing none.
Size normalization is what makes it work — `1.7 fl oz` and `50ml` resolve to the
same value, while `50ml` and `100ml` are held apart.

## On scraping and robots.txt

Every request is checked against the target's `robots.txt` before it is sent, and
the crawler identifies itself honestly as `XLBSkincareBot` rather than spoofing a
browser. Retailers that disallow us are not crawled — see `EXCLUDED_RETAILERS` in
`backend/app/scrapers/registry.py`, which records who was excluded and why.

Adding a Shopify retailer is one entry in `SHOPIFY_RETAILERS`. Adding any other
retailer is one `RetailerScraper` subclass plus a registry entry; nothing else in
the system needs to know a new source exists.

## Layout

```
backend/app/
  models/      SQLAlchemy models
  scrapers/    base interface, robots, fetch, per-retailer implementations
  services/    text normalization, matching, INCI parsing, analysis, scoring
  jobs/        seeding, ingestion, scheduled refresh
  api/         FastAPI routers
  data/        brand list, INCI dictionary, conflict rules
frontend/src/
  pages/       Home, Search, Product, Quiz, Results, Compare
  components/  ProductCard, PriceTable, IngredientList, PriceChart
```

## Data

The catalog ships as **synthetic seed data** (`app/data/seed_products.py`): 44
plausible skincare products with realistic INCI lists, priced across 4 fictional
retailers with 90 days of generated history. Formulas are representative rather
than transcriptions of any real label, and the retailer names are deliberately
fictional — none of it should be read as real pricing.

The live ingestion path (`app/scrapers/`) is built and works against real
sources, but is not what populates the app today.

## Status

Working end to end on seed data. Not yet done:

- Alembic migrations (schema is `create_all` for now)
- Ingestion wired to the live scrapers as the default data source
- Product images (seed data has none)
- Frontend tests, and a Compare page for viewing products side by side
