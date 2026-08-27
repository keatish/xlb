"""Scope filtering is what keeps non-skincare out of a skincare catalog.

classify_category() will happily file anything as TREATMENT, so is_in_scope() is
the only thing standing between the retailer's full range and the product table.
Every case here is a real title from Soko Glam's live catalog feed.
"""

import pytest

from app.jobs.ingest import is_in_scope


class TestOutOfScope:
    @pytest.mark.parametrize(
        "product_type,title",
        [
            # Merchandise. product_type "SWAG" is the only reliable signal; the
            # title alone reads like nothing in particular.
            ("SWAG", "Soko Glam Logo Baseball Cap"),
            ("SWAG", "Soko Glam Tote Bag"),
            # Body care - adjacent to skincare, but out of the README's scope.
            # Soko Glam files the whole range under product_type "Body".
            ("Body", "The Glow Getter Multi-Oil Body Butter"),
            ("Body", "Urea 5% Body Serum"),
            ("Body", "The Calmer Ceramide Body Wash"),
            ("Body", "Beta Panthenol Repair Body Cream"),
            ("Body", "Supermochi Body Exfoliator+"),
            # Sets: no single INCI list, size or barcode, so not one canonical SKU.
            ("Skincare Set", "10-Step Korean Skin Care Routine Set"),
            ("Skincare Set", "5-Step Anti-Aging Set"),
            (None, "Rise and Shine Set"),
            # Haircare, makeup, tools, fragrance.
            ("Hair Brush", "Flex Gentle Brush"),
            ("Hair Treatment", "Annatto Hair Oil"),
            ("Lip Color", "Effortless Glow Lip Oil"),
            ("Tools", "Beauty Beam Rejuvenating Red"),
            ("BB/CC Cream", "BB Creme Au Ginseng"),
        ],
    )
    def test_rejected(self, product_type, title):
        assert not is_in_scope(product_type, title)

    def test_body_care_rejected_by_tag_when_type_is_blank(self):
        assert not is_in_scope(None, "Supercloud Serum+", ["body care", "Body Lotion"])

    def test_swag_rejected_by_tag_when_type_is_blank(self):
        assert not is_in_scope(None, "Logo Water Bottle", ["swag", "exclusive"])


class TestInScope:
    @pytest.mark.parametrize(
        "product_type,title",
        [
            ("Water Cleanser", "Blank Slate Gentle Gel Cleanser"),
            ("Toner", "Safe me. Relief Essence Toner"),
            ("Serum/Ampoule", "Black Rice Night Knight Retinol Serum"),
            ("Facial Moisturizer", "Always Youth Cream"),
            ("Sunscreen", "Madecassoside Moisture Sun Serum"),
            ("Sheet Mask", "Ceramide Essential Mask Moisture Barrier (4 pack)"),
            ("Eye Mask", "Retinol Collagen Eye Ampoule Patch"),
            ("Wash Off Masks", "Rosé Resurfacing Facial Mask"),
            (None, "Mr. Reliable Lightweight Moisturizer"),
        ],
    )
    def test_accepted(self, product_type, title):
        assert is_in_scope(product_type, title)

    def test_a_skincare_tag_beats_an_ambiguous_tag(self):
        # "hair" appears in plenty of legitimate skincare tag soup; an explicit
        # skincare tag is what breaks the tie.
        assert is_in_scope("Serum", "Niacinamide Serum", ["hair", "skincare", "serum"])

    def test_cap_marker_does_not_match_capsule(self):
        # " cap " is space-anchored precisely so this keeps working.
        assert is_in_scope("Serum", "Time Capsule Retinol Serum")
