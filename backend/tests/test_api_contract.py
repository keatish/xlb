"""Contract checks on the generated OpenAPI schema.

Deliberately schema-only: no database, no fixtures. The realistic failure here
is declaring `avoid: list[str]` without `Query(...)`, which FastAPI silently
reads as a single string - so `?avoid=fragrance&avoid=lanolin` would screen for
one term and quietly ignore the rest. That is a wrong "no allergens found",
which is the one answer this feature must never get wrong by accident.
"""

from __future__ import annotations

import pytest

from app.main import app

SCREENED_ROUTES = ["/api/products", "/api/products/deals", "/api/products/{slug}"]


@pytest.fixture(scope="module")
def spec() -> dict:
    return app.openapi()


@pytest.mark.parametrize("path", SCREENED_ROUTES)
def test_avoid_is_a_repeatable_query_param(spec: dict, path: str) -> None:
    params = {p["name"]: p for p in spec["paths"][path]["get"].get("parameters", [])}
    assert "avoid" in params, f"{path} cannot be screened"
    schema = params["avoid"]["schema"]
    assert schema.get("type") == "array", f"{path} would collapse avoid to one term"
    assert schema["items"]["type"] == "string"
    assert params["avoid"]["required"] is False


def test_quiz_accepts_an_avoid_list(spec: dict) -> None:
    props = spec["components"]["schemas"]["QuizRequest"]["properties"]
    assert props["avoid_ingredients"]["type"] == "array"


def test_quiz_reports_what_it_withheld(spec: dict) -> None:
    """A shorter list of recommendations must be explainable."""
    props = spec["components"]["schemas"]["QuizResponse"]["properties"]
    assert "excluded" in props
    assert "allergen_terms" in props


def test_product_summary_carries_its_own_screen(spec: dict) -> None:
    """Cards and detail read the same field, so they cannot disagree."""
    assert "allergens" in spec["components"]["schemas"]["ProductSummary"]["properties"]


def test_allergen_options_endpoint_exists(spec: dict) -> None:
    assert "/api/allergens" in spec["paths"]
