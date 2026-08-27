"""Allergen screening: resolving what the user typed, and finding it in a list."""

from __future__ import annotations

from app.services.allergens import resolve_terms, screen
from app.services.analysis import analyze


def resolve_one(term: str):
    resolved = resolve_terms([term])
    assert len(resolved) == 1, f"{term!r} resolved to {len(resolved)} terms"
    return resolved[0]


def screen_for(names: list[str], terms: list[str]):
    return screen(analyze(names), resolve_terms(terms))


class TestResolvingWhatTheUserTyped:
    def test_fragrance_expands_to_the_whole_eu_panel(self):
        term = resolve_one("fragrance")
        assert term.kind == "group"
        # The point of the group: these are never spelled "fragrance" on a label.
        for component in ("linalool", "limonene", "geraniol", "citronellol"):
            assert component in term.members
        assert len(term.members) >= 28

    def test_synonyms_land_on_the_same_group(self):
        keys = {resolve_one(word).key for word in ("fragrance", "Parfum", "PERFUME", "scent")}
        assert keys == {"fragrance"}

    def test_group_key_round_trips(self):
        """The frontend sends back a key it got from /api/allergens."""
        assert resolve_one("nut_oils").key == "nut_oils"
        assert resolve_one("Nut and seed oils").key == "nut_oils"

    def test_a_plain_ingredient_resolves_through_the_existing_alias_table(self):
        term = resolve_one("vitamin e")
        assert term.kind == "ingredient"
        assert term.key == "Tocopherol"

    def test_unknown_input_is_kept_and_flagged_not_dropped(self):
        term = resolve_one("ceramidde")
        assert term.kind == "unrecognized"
        assert not term.recognized
        assert term.members  # still searched for literally

    def test_blanks_and_duplicates_collapse(self):
        assert resolve_terms(["", "   ", None]) == []
        assert len(resolve_terms(["Fragrance", "fragrance", " FRAGRANCE "])) == 1


class TestFindingThemInAProduct:
    def test_a_fragrance_component_is_caught_without_the_word_fragrance(self):
        result = screen_for(["Water", "Glycerin", "Niacinamide", "Linalool"], ["fragrance"])
        assert result.flagged
        assert [h.inci_name for h in result.hits] == ["Linalool"]
        assert result.hits[0].position == 4

    def test_hit_names_the_group_it_came_from(self):
        hit = screen_for(["Water", "Limonene"], ["fragrance"]).hits[0]
        assert hit.group_label == "Fragrance"
        assert "fragrance ingredient you avoid" in hit.summary

    def test_hit_on_the_term_itself_does_not_say_it_twice(self):
        hit = screen_for(["Water", "Fragrance"], ["fragrance"]).hits[0]
        assert hit.summary == "Fragrance / Parfum, which you avoid"

    def test_position_drives_prominence(self):
        early = screen_for(["Water", "Lanolin", "Glycerin"], ["lanolin"]).hits[0]
        late = screen_for(["Water"] * 20 + ["Lanolin"], ["lanolin"]).hits[0]
        assert early.prominent
        assert not late.prominent

    def test_hits_are_ordered_by_position(self):
        result = screen_for(
            ["Water", "Limonene", "Glycerin", "Fragrance", "Linalool"], ["fragrance"]
        )
        assert [h.position for h in result.hits] == [2, 4, 5]

    def test_an_ingredient_counts_once_even_if_two_terms_cover_it(self):
        result = screen_for(["Water", "Lanolin"], ["fragrance", "lanolin", "contact allergens"])
        assert len(result.hits) == 1

    def test_substring_collisions_do_not_fire(self):
        """'alcohol' must not flag cetyl/cetearyl alcohol - they are emollients.

        Width comes from group expansion, never from substring matching.
        """
        result = screen_for(["Water", "Cetyl Alcohol", "Cetearyl Alcohol"], ["alcohol"])
        assert not result.flagged

    def test_unrelated_avoid_list_leaves_a_product_clear(self):
        result = screen_for(["Water", "Glycerin", "Niacinamide"], ["lanolin"])
        assert not result.flagged
        assert result.verdict == "clear"


class TestHonestNegatives:
    def test_unreadable_ingredients_downgrade_a_clean_result(self):
        """We cannot call a product clear when we could not read all of it."""
        result = screen_for(["Water", "Glycerin", "Somethingnobodyknows"], ["lanolin"])
        assert not result.flagged
        assert result.unknown_count == 1
        assert result.verdict == "incomplete"

    def test_a_product_with_no_ingredient_list_is_never_clear(self):
        result = screen_for([], ["lanolin"])
        assert result.verdict == "incomplete"
        assert not result.screened

    def test_unrecognized_terms_are_reported_back(self):
        result = screen_for(["Water"], ["fragrance", "ceramidde"])
        assert result.unrecognized == ["ceramidde"]

    def test_a_hit_outranks_incomplete_coverage(self):
        result = screen_for(["Lanolin", "Somethingnobodyknows"], ["lanolin"])
        assert result.verdict == "flagged"

    def test_no_terms_means_no_verdict_worth_showing(self):
        result = screen_for(["Water", "Lanolin"], [])
        assert not result.flagged


class TestGroupsMatchRealFormulas:
    def test_parabens(self):
        result = screen_for(["Water", "Methylparaben", "Propylparaben"], ["parabens"])
        assert len(result.hits) == 2

    def test_sulfates_via_abbreviation(self):
        result = screen_for(["Water", "Sodium Laureth Sulfate"], ["SLS"])
        assert result.flagged

    def test_nut_oils_catch_a_botanical_name_a_user_would_not_know(self):
        result = screen_for(["Water", "Prunus Amygdalus Dulcis Oil"], ["almond"])
        assert result.flagged
        assert result.hits[0].common_name == "Sweet Almond Oil"

    def test_isothiazolinone_preservatives(self):
        result = screen_for(["Water", "Methylisothiazolinone"], ["MI"])
        assert result.flagged
