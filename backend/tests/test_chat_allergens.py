"""Tests for allergen resolution and filtering.

This is the safety-critical half of the chat feature: if resolution or filtering
is wrong, the assistant recommends something the user told it not to. The model
is not involved in any of it, which is exactly why it can be tested directly.
"""

from __future__ import annotations

from app.chat.allergens import blocked_reason, resolve
from app.chat.tools import (
    apply_allergen_filter,
    format_allergen_state,
    format_ingredients,
    format_prices,
)
from app.services.analysis import analyze


# --- resolution -------------------------------------------------------------


def test_resolves_exact_inci_name():
    resolved = resolve(["Salicylic Acid"])
    assert "Salicylic Acid" in resolved.inci_names
    assert not resolved.unresolved


def test_resolves_case_and_spacing_variations():
    assert resolve(["  salicylic   acid "]).inci_names == resolve(["Salicylic Acid"]).inci_names


def test_resolves_by_common_name():
    # The dictionary lists Niacinamide with common name "Niacinamide (Vitamin B3)",
    # so a user typing "vitamin b3" should still land on it.
    resolved = resolve(["vitamin b3"])
    assert any("Niacinamide" in name for name in resolved.inci_names)


def test_resolves_ingredient_classes():
    assert resolve(["fragrance"]).groups == {"fragrance"}
    assert resolve(["Essential Oils"]).groups == {"essential_oil"}
    assert resolve(["ethanol"]).groups == {"alcohol"}


def test_unknown_term_is_reported_not_silently_dropped():
    resolved = resolve(["unobtainium extract"])
    assert resolved.unresolved == ["unobtainium extract"]
    assert not resolved.inci_names


def test_very_short_terms_do_not_substring_match():
    # "oil" would otherwise knock out most of the catalog.
    resolved = resolve(["oil"])
    assert not resolved.inci_names


def test_empty_and_blank_input():
    assert not resolve(None).active
    assert not resolve([]).active
    assert not resolve(["", "   "]).active


def test_labels_lists_classes_and_ingredients():
    labels = resolve(["fragrance", "Salicylic Acid"]).labels()
    assert "fragrance" in labels
    assert "Salicylic Acid" in labels


# --- blocking ---------------------------------------------------------------


def test_no_allergens_blocks_nothing():
    analysis = analyze(["Water", "Salicylic Acid"])
    assert blocked_reason(analysis, resolve([])) is None


def test_blocks_on_named_ingredient():
    analysis = analyze(["Water", "Glycerin", "Salicylic Acid"])
    reason = blocked_reason(analysis, resolve(["salicylic acid"]))
    assert reason is not None
    assert "Salicylic Acid" in reason or "BHA" in reason


def test_blocks_on_fragrance_class():
    analysis = analyze(["Water", "Glycerin", "Fragrance"])
    assert blocked_reason(analysis, resolve(["fragrance"])) == "contains fragrance"


def test_blocks_on_essential_oil_class():
    analysis = analyze(["Water", "Melaleuca Alternifolia Leaf Oil"])
    assert blocked_reason(analysis, resolve(["essential oils"])) == "contains essential oils"


def test_allows_product_without_the_allergen():
    analysis = analyze(["Water", "Glycerin", "Ceramide NP"])
    assert blocked_reason(analysis, resolve(["fragrance", "salicylic acid"])) is None


def test_unresolved_term_blocks_nothing():
    """An allergen we could not resolve must not silently filter everything."""
    analysis = analyze(["Water", "Glycerin"])
    resolved = resolve(["unobtainium"])
    assert blocked_reason(analysis, resolved) is None


# --- filtering --------------------------------------------------------------


def test_filter_separates_kept_from_skipped():
    clean = analyze(["Water", "Glycerin", "Ceramide NP"])
    scented = analyze(["Water", "Glycerin", "Fragrance"])
    rows = [
        (1, clean, {"brand": "A", "name": "Clean", "slug": "clean"}),
        (2, scented, {"brand": "B", "name": "Scented", "slug": "scented"}),
    ]

    result = apply_allergen_filter(rows, resolve(["fragrance"]))

    assert [p["slug"] for p in result["products"]] == ["clean"]
    assert result["skipped_for_allergens"] == 1
    assert result["skipped"][0]["reason"] == "contains fragrance"
    assert "Scented" in result["skipped"][0]["name"]


def test_filter_is_a_passthrough_with_no_allergens():
    analysis = analyze(["Water", "Fragrance"])
    rows = [(1, analysis, {"brand": "A", "name": "Anything", "slug": "anything"})]

    result = apply_allergen_filter(rows, resolve([]))

    assert len(result["products"]) == 1
    assert "skipped_for_allergens" not in result


# --- formatters -------------------------------------------------------------


def test_format_prices_sorts_and_reports_spread():
    prices = [
        {"retailer": "Dear", "price": 20.0, "in_stock": True},
        {"retailer": "Cheap", "price": 12.5, "in_stock": True},
        {"retailer": "Unpriced", "price": None, "in_stock": True},
    ]
    out = format_prices(prices, history_low=11.0)

    assert [r["retailer"] for r in out["retailers"]] == ["Cheap", "Dear"]
    assert out["cheapest"] == "Cheap"
    assert out["spread"] == 7.5
    assert out["ninety_day_low"] == 11.0


def test_format_prices_with_nothing_priced():
    out = format_prices([{"retailer": "X", "price": None, "in_stock": False}])
    assert out["retailers"] == []
    assert "cheapest" not in out


def test_format_ingredients_reports_flags_and_order():
    out = format_ingredients(analyze(["Water", "Niacinamide", "Fragrance"]))
    assert out["count"] == 3
    assert out["inci_order"][0] == "Water"
    assert out["has_fragrance"] is True
    assert any("Niacinamide" in a["name"] for a in out["actives"])


def test_format_allergen_state_flags_unrecognised_terms():
    out = format_allergen_state(resolve(["fragrance", "unobtainium"]))
    assert "fragrance" in out["avoiding"]
    assert out["not_recognised"] == ["unobtainium"]
    assert "NOT being filtered" in out["note"]


# --- currency ---------------------------------------------------------------
#
# A price without a currency is a price the model has to guess a symbol for, and
# an observed run guessed wrong - USD figures rendered with a pound sign. Every
# payload carrying a price must therefore carry its currency.


class _FakeSummary:
    slug = "x"
    brand = "Brand"
    name = "Product"
    category = "serum"
    size_label = "30ml"
    best_price = 12.5
    retailer_count = 3
    on_sale = False
    key_actives: list[str] = []


def test_format_summary_always_includes_a_currency():
    from app.chat.tools import format_summary

    assert format_summary(_FakeSummary())["currency"] == "USD"
    assert format_summary(_FakeSummary(), currency="SGD")["currency"] == "SGD"


def test_format_prices_reports_the_currency_of_its_rows():
    rows = [{"retailer": "A", "price": 10.0, "in_stock": True, "currency": "SGD"}]
    assert format_prices(rows, currency="SGD")["currency"] == "SGD"


def test_currency_helper_prefers_the_row_value_over_the_default():
    from app.chat.tools import DEFAULT_CURRENCY, _currency_of

    assert _currency_of([{"currency": "EUR"}]) == "EUR"
    assert _currency_of([{}]) == DEFAULT_CURRENCY
    assert _currency_of([]) == DEFAULT_CURRENCY
