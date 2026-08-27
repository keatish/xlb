"""INCI parsing, ingredient analysis, conflict rules, dupes and quiz scoring."""

import pytest

from app.services.analysis import analyze, detect_conflicts
from app.services.dupes import find_dupes, similarity
from app.services.inci import lookup, normalize_name_list, parse_ingredients
from app.services.recommend import SkinProfile, build_routine, rank, score_product

MESSY_LABEL = """Ingredients: Water, Snail Secretion Filtrate (92%), Betaine,
1,2-Hexanediol, Butyrospermum Parkii (Shea) Butter*, Phenoxyethanol, Aqua,
Panthenol, Tocopherol, Parfum. May contain: CI 77891, Mica."""


class TestInciParsing:
    def test_parses_a_messy_real_world_label(self):
        parsed = parse_ingredients(MESSY_LABEL)
        assert parsed[0] == "Water"
        assert "Snail Secretion Filtrate" in parsed

    def test_water_and_aqua_collapse_to_one_entry(self):
        assert parse_ingredients(MESSY_LABEL).count("Water") == 1

    def test_parfum_canonicalizes_to_fragrance(self):
        assert "Fragrance" in parse_ingredients(MESSY_LABEL)

    def test_may_contain_tail_is_dropped(self):
        parsed = parse_ingredients(MESSY_LABEL)
        assert not any("CI 77891" in name or name == "Mica" for name in parsed)

    def test_parenthetical_is_stripped_but_name_kept(self):
        assert "Butyrospermum Parkii Butter" in parse_ingredients(MESSY_LABEL)

    @pytest.mark.parametrize("name", ["1,2-Hexanediol", "1,3-Butylene Glycol"])
    def test_internal_commas_survive_the_split(self, name):
        # Splitting naively on commas shreds these into "1" and "2-Hexanediol".
        assert name in parse_ingredients(f"Water, {name}, Glycerin")

    def test_aliases_normalize(self):
        assert normalize_name_list(["Snail Mucin", "Vitamin E"]) == [
            "Snail Secretion Filtrate",
            "Tocopherol",
        ]

    def test_empty_input(self):
        assert parse_ingredients(None) == []
        assert parse_ingredients("") == []


class TestAnalysis:
    def test_flags_actives_irritants_and_comedogenics(self):
        result = analyze(["Water", "Niacinamide", "Fragrance", "Cocos Nucifera Oil"])
        assert "niacinamide" in result.active_groups
        assert result.has_fragrance
        assert result.max_comedogenic == 4

    def test_position_weighting(self):
        # An active at position 2 should count for more than the same active at 20.
        high = analyze(["Water", "Retinol"])
        low = analyze(["Water"] * 19 + ["Retinol"])
        assert high.group_weight("retinoid") > low.group_weight("retinoid")

    def test_unknown_ingredients_are_counted_not_dropped(self):
        result = analyze(["Water", "Totally Made Up Extract"])
        assert result.unknown_count == 1
        assert len(result.ingredients) == 2


class TestConflicts:
    def test_retinoid_plus_aha_is_high_severity(self):
        found = detect_conflicts(
            [("Retinal Serum", analyze(["Water", "Retinal"])),
             ("Glycolic Toner", analyze(["Water", "Glycolic Acid"]))]
        )
        assert any(c["id"] == "retinoid_aha" and c["severity"] == "high" for c in found)

    def test_compatible_pair_produces_nothing(self):
        found = detect_conflicts(
            [("Niacinamide", analyze(["Water", "Niacinamide"])),
             ("HA Serum", analyze(["Water", "Sodium Hyaluronate"]))]
        )
        assert found == []

    def test_single_product_with_both_actives_does_not_conflict(self):
        # A brand shipping both in one bottle balanced them; that is not our warning to give.
        found = detect_conflicts([("Combo", analyze(["Water", "Retinal", "Glycolic Acid"]))])
        assert found == []


class TestDupes:
    def test_shared_base_alone_is_not_a_dupe(self):
        a = analyze(["Water", "Glycerin", "Phenoxyethanol", "Retinol"])
        b = analyze(["Water", "Glycerin", "Phenoxyethanol", "Salicylic Acid"])
        results = find_dupes(1, a, 20.0, "serum", [(2, b, 10.0, "serum")])
        assert results == []

    def test_similar_formula_with_shared_active_is_a_dupe(self):
        a = analyze(["Water", "Niacinamide", "Zinc PCA", "Glycerin"])
        b = analyze(["Water", "Niacinamide", "Zinc PCA", "Propanediol"])
        results = find_dupes(1, a, 20.0, "serum", [(2, b, 8.0, "serum")])
        assert len(results) == 1
        assert results[0].savings == 12.0

    def test_more_expensive_candidates_are_excluded(self):
        a = analyze(["Water", "Niacinamide", "Zinc PCA"])
        b = analyze(["Water", "Niacinamide", "Zinc PCA"])
        assert find_dupes(1, a, 10.0, "serum", [(2, b, 30.0, "serum")]) == []

    def test_identical_lists_are_maximally_similar(self):
        a = analyze(["Water", "Niacinamide", "Zinc PCA"])
        assert similarity(a, a) == 1.0


class TestRecommendation:
    def test_concern_match_produces_a_reason(self):
        result = score_product(
            1, analyze(["Water", "Niacinamide"]),
            SkinProfile(skin_type="oily", concerns=["oiliness"]),
            price=10.0,
        )
        assert result.score > 0
        assert any("Niacinamide" in reason for reason in result.reasons)

    def test_sensitive_skin_penalizes_fragrance(self):
        profile = SkinProfile(skin_type="normal", concerns=["dryness"], sensitive=True)
        plain = score_product(1, analyze(["Water", "Glycerin"]), profile, price=10.0)
        scented = score_product(2, analyze(["Water", "Glycerin", "Fragrance"]), profile, price=10.0)
        assert scented.score < plain.score
        assert any("fragrance" in w.lower() for w in scented.warnings)

    def test_acne_prone_penalizes_comedogenic_ingredients(self):
        profile = SkinProfile(skin_type="oily", concerns=["acne"], acne_prone=True)
        clean = score_product(1, analyze(["Water", "Salicylic Acid"]), profile, price=10.0)
        clogging = score_product(
            2, analyze(["Water", "Salicylic Acid", "Isopropyl Myristate"]), profile, price=10.0
        )
        assert clogging.score < clean.score

    def test_over_budget_is_penalized_and_flagged(self):
        profile = SkinProfile(skin_type="normal", concerns=["dryness"], budget_max=20.0)
        cheap = score_product(1, analyze(["Water", "Ceramide NP"]), profile, price=15.0)
        dear = score_product(2, analyze(["Water", "Ceramide NP"]), profile, price=60.0)
        assert dear.score < cheap.score
        assert any("budget" in w.lower() for w in dear.warnings)

    def test_rank_drops_products_with_no_reason(self):
        # Inert filler only: nothing matches the concern and nothing is preferred
        # for this skin type, so there is nothing to tell the user.
        unexplained = score_product(
            1,
            analyze(["Water", "Xanthan Gum", "Phenoxyethanol"]),
            SkinProfile(skin_type="normal", concerns=["acne"]),
        )
        assert unexplained.reasons == []
        assert rank([unexplained]) == []

    def test_routine_places_sunscreen_am_and_exfoliant_pm(self):
        routine = build_routine([(1, "sunscreen"), (2, "exfoliant"), (3, "moisturizer")])
        assert 1 in routine["am"] and 1 not in routine["pm"]
        assert 2 in routine["pm"] and 2 not in routine["am"]
        assert 3 in routine["am"] and 3 in routine["pm"]

    def test_cleanser_comes_before_moisturizer(self):
        routine = build_routine([(1, "moisturizer"), (2, "cleanser")])
        assert routine["am"].index(2) < routine["am"].index(1)


class TestIngredientDictionary:
    @pytest.mark.parametrize(
        "name,active,irritant",
        [("Niacinamide", True, False), ("Fragrance", False, True), ("Retinol", True, True)],
    )
    def test_known_ingredients(self, name, active, irritant):
        entry = lookup(name)
        assert entry is not None
        assert entry["is_active"] is active
        assert entry["is_irritant"] is irritant
