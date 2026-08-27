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

Alongside it, `app/jobs/ingest.py` pulls **real** products from the retailers in
`scrapers/registry.py` and writes them into the same schema:

```bash
python -m app.jobs.ingest --limit 10 --dry-run   # fetch and report, write nothing
python -m app.jobs.ingest --limit 10             # write
```

Per product it discovers in-scope skincare from the retailer's public catalog
feed, fetches the full record (barcode, image, description), enriches the INCI
list from INCIDecoder — retailers do not publish ingredients — derives concern
weights from that list so the product answers the quiz, then looks for the same
SKU at a second retailer so there is a price to compare. It is idempotent:
re-running matches on barcode, then slug, and appends a price snapshot rather
than duplicating the catalog.

Two things worth knowing about live rows:

- **Ingredients are best-effort.** Roughly half of products have no confident
  INCIDecoder match, so they land with no INCI list and therefore no concerns,
  and are invisible to the quiz. That is a coverage gap, not an error.
- **Sizes are usually absent.** Neither retailer publishes size in a parseable
  field, so `size_value` is null and the size gate in matching cannot help.
  Barcode matching carries the weight instead, which is why cross-retailer
  matches come back at confidence 1.0 or not at all.

Scope is enforced in `ingest.py`, not in `classify_category()` — that function is
a classifier with a `TREATMENT` fallback, so left to itself it will happily file
a hair brush as skincare.

## Status

Working end to end. Not yet done:

- Alembic migrations (schema is `create_all` for now)
- Scheduled ingestion (the job is manual; only price refresh is scheduled)
- Ingredient coverage for live products without an INCIDecoder match
- Frontend tests, and a Compare page for viewing products side by side
