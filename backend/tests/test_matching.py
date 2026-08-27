"""Matching is where a bug shows a user the wrong price, so the negative cases
matter more than the positive ones."""

import pytest

from app.services.matching import build_candidate, classify_category, compare
from app.services.text import clean_product_name, parse_price, parse_size, sizes_match


class TestSizeNormalization:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("COSRX Snail Essence 100ml", (100.0, "ml")),
            ("CeraVe Moisturizing Cream 1.7 fl oz", (50.27, "ml")),
            ("Toner 150 mL", (150.0, "ml")),
            ("Lip Mask 20g", (20.0, "g")),
            ("Cream 16 oz", (453.59, "g")),
            ("no size at all", (None, None)),
        ],
    )
    def test_parse_size(self, text, expected):
        assert parse_size(text) == expected

    def test_fluid_ounces_equal_millilitres(self):
        oz_value, oz_unit = parse_size("1.7 fl oz")
        assert sizes_match(oz_value, oz_unit, 50.0, "ml")

    def test_different_sizes_never_match(self):
        assert not sizes_match(50.0, "ml", 100.0, "ml")

    def test_unknown_size_is_permissive(self):
        # Many listings omit size; refusing these would lose most of the catalog.
        assert sizes_match(None, None, 50.0, "ml")


class TestProductMatching:
    def test_identical_barcode_is_definitive(self):
        a = build_candidate("COSRX", "Advanced Snail 92 Cream", upc="8809416470016")
        b = build_candidate("Cosrx", "Cosrx Advanced Snail 92 All In One Cream", upc="8809416470016")
        result = compare(a, b)
        assert result.matched
        assert result.confidence == 1.0

    def test_different_barcodes_never_match(self):
        a = build_candidate("COSRX", "Snail Essence", upc="8809598452350")
        b = build_candidate("COSRX", "Snail Essence", upc="8809416470016")
        assert not compare(a, b).matched

    def test_fuzzy_match_without_barcode(self):
        a = build_candidate("COSRX", "Advanced Snail 92 All In One Cream 100ml", 100.0, "ml")
        b = build_candidate("Cosrx", "Cosrx Advanced Snail 92 All-In-One Cream")
        assert compare(a, b).matched

    def test_same_name_different_size_does_not_match(self):
        a = build_candidate("COSRX", "Snail Cream 100ml", 100.0, "ml")
        b = build_candidate("COSRX", "Snail Cream 50ml", 50.0, "ml")
        assert not compare(a, b).matched

    def test_same_name_different_brand_does_not_match(self):
        a = build_candidate("Anua", "Heartleaf 77% Toner 250ml", 250.0, "ml")
        b = build_candidate("Beauty of Joseon", "Heartleaf 77% Toner 250ml", 250.0, "ml")
        assert not compare(a, b).matched

    def test_multipack_is_a_different_sku(self):
        a = build_candidate("COSRX", "Acne Pimple Master Patch 24 count")
        b = build_candidate("COSRX", "Acne Pimple Master Patch 10 count")
        assert not compare(a, b).matched


class TestNameCleaning:
    def test_strips_brand_size_and_marketing_noise(self):
        cleaned = clean_product_name("NEW! Anua Heartleaf 77% Soothing Toner 250ml (Official)", "Anua")
        assert cleaned == "heartleaf 77% soothing toner"

    @pytest.mark.parametrize(
        "raw,expected",
        [("$18.00", 18.0), ("1.234,56", 1234.56), ("USD 10.40", 10.4), (21.0, 21.0), ("", None)],
    )
    def test_parse_price(self, raw, expected):
        assert parse_price(raw) == expected


class TestCategoryClassification:
    @pytest.mark.parametrize(
        "product_type,title,expected",
        [
            ("Water Cleanser", "Gel Cleanser", "cleanser"),
            ("Moisturizer", "All In One Cream", "moisturizer"),
            (None, "Relief Sun SPF50", "sunscreen"),
            (None, "Snail 96 Mucin Power Essence", "essence"),
            ("Serum", "Vitamin C 13 Serum", "serum"),
        ],
    )
    def test_classify(self, product_type, title, expected):
        assert classify_category(product_type, title).value == expected
