"""Allergen screening.

The user types what they react to; this turns that into a set of INCI names and
reports where those names appear in a product's ingredient list.

Two things make this more than a substring search:

1. **Group expansion.** Someone who says "fragrance" means the whole class, not
   the literal word. Products that declare `Linalool` and `Limonene` but never
   the word "Parfum" are exactly the ones that catch people out, so a group term
   expands to every member named in `conflicts.json`.

2. **Honest negatives.** A product whose list we could not fully identify cannot
   be called clear. `unknown_count` from the analysis is carried through to the
   verdict so the UI can say "nothing found, but we could not read everything"
   rather than implying safety.

Deliberately kept out of the ingredient dictionary: `is_irritant` already means
"this stings" (kojic acid is flagged, and it is not an allergen), so allergen
membership lives in `conflicts.json` instead of overloading that flag.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.analysis import HIGH_POSITION_CUTOFF, Analysis, config
from app.services.inci import canonicalize, ingredient_dictionary, lookup
from app.services.text import normalize_text


@dataclass(slots=True)
class AllergenTerm:
    """One thing the user said they avoid, resolved against what we know."""

    query: str
    label: str
    members: frozenset[str]
    kind: str = "ingredient"  # "group" | "ingredient" | "unrecognized"
    key: str | None = None
    note: str | None = None

    @property
    def recognized(self) -> bool:
        return self.kind != "unrecognized"


@dataclass(slots=True)
class AllergenHit:
    inci_name: str
    position: int
    matched: str
    common_name: str | None = None
    group_label: str | None = None
    prominent: bool = False

    @property
    def summary(self) -> str:
        """Why this ingredient was flagged, in the user's terms.

        Naming the group matters when the ingredient name gives no clue: nobody
        types "Limonene", they type "fragrance".
        """
        name = self.common_name or self.inci_name
        if self.group_label and normalize_text(self.group_label) != normalize_text(self.inci_name):
            return f"{name}, a {self.group_label.lower()} ingredient you avoid"
        return f"{name}, which you avoid"


@dataclass(slots=True)
class AllergenScreen:
    hits: list[AllergenHit] = field(default_factory=list)
    unrecognized: list[str] = field(default_factory=list)
    unknown_count: int = 0
    screened: bool = True

    @property
    def flagged(self) -> bool:
        return bool(self.hits)

    @property
    def verdict(self) -> str:
        """`flagged` | `clear` | `incomplete` - never a bare "safe"."""
        if self.hits:
            return "flagged"
        if not self.screened or self.unknown_count:
            return "incomplete"
        return "clear"

    @property
    def matched_names(self) -> list[str]:
        seen: dict[str, None] = {}
        for hit in self.hits:
            seen.setdefault(hit.common_name or hit.inci_name, None)
        return list(seen)


def allergen_groups() -> list[dict]:
    return config().get("allergen_groups", [])


def _group_index() -> dict[str, dict]:
    return {group["key"]: group for group in allergen_groups()}


def _synonym_table() -> dict[str, str]:
    """Normalized user phrasing -> group key.

    Group labels and keys resolve too, so the frontend can round-trip a key it
    was given by `/api/allergens` without needing the synonym list.
    """
    table = {
        normalize_text(phrase): key
        for phrase, key in config().get("allergen_synonyms", {}).items()
    }
    for group in allergen_groups():
        table.setdefault(normalize_text(group["key"]), group["key"])
        table.setdefault(normalize_text(group["key"].replace("_", " ")), group["key"])
        table.setdefault(normalize_text(group["label"]), group["key"])
    return table


def resolve_terms(terms: list[str]) -> list[AllergenTerm]:
    """Turn raw user input into resolved terms, dropping blanks and duplicates.

    An input we cannot place is still returned, with `kind="unrecognized"` and
    the cleaned string as its only member. It is searched for literally - the
    alternative is silently ignoring it, which would tell someone their allergen
    is absent when we simply never looked.
    """
    groups = _group_index()
    synonyms = _synonym_table()
    dictionary = ingredient_dictionary()

    resolved: list[AllergenTerm] = []
    seen: set[str] = set()

    for raw in terms:
        query = (raw or "").strip()
        if not query:
            continue
        key = normalize_text(query)
        if not key or key in seen:
            continue
        seen.add(key)

        group_key = synonyms.get(key)
        if group_key and group_key in groups:
            group = groups[group_key]
            resolved.append(
                AllergenTerm(
                    query=query,
                    label=group["label"],
                    members=frozenset(normalize_text(m) for m in group["members"]),
                    kind="group",
                    key=group_key,
                    note=group.get("note"),
                )
            )
            continue

        canonical = canonicalize(query)
        entry = lookup(canonical) or dictionary.get(key)
        if entry:
            resolved.append(
                AllergenTerm(
                    query=query,
                    label=entry.get("common_name") or entry["inci_name"],
                    members=frozenset({normalize_text(entry["inci_name"])}),
                    kind="ingredient",
                    key=entry["inci_name"],
                    note=entry.get("description"),
                )
            )
            continue

        resolved.append(
            AllergenTerm(
                query=query,
                label=query,
                members=frozenset({key, normalize_text(canonical)} - {""}),
                kind="unrecognized",
            )
        )

    return resolved


def screen(analysis: Analysis | None, terms: list[AllergenTerm]) -> AllergenScreen:
    """Find every ingredient in `analysis` that one of `terms` covers."""
    result = AllergenScreen(
        unrecognized=[t.query for t in terms if not t.recognized],
        unknown_count=analysis.unknown_count if analysis else 0,
        screened=bool(analysis and analysis.ingredients),
    )
    if not terms or not analysis:
        return result

    for ingredient in analysis.ingredients:
        name_key = normalize_text(ingredient.inci_name)
        if not name_key:
            continue
        for term in terms:
            if name_key not in term.members:
                continue
            result.hits.append(
                AllergenHit(
                    inci_name=ingredient.inci_name,
                    position=ingredient.position,
                    matched=term.query,
                    common_name=ingredient.common_name,
                    group_label=term.label if term.kind == "group" else None,
                    prominent=ingredient.position <= HIGH_POSITION_CUTOFF,
                )
            )
            break  # one hit per ingredient, attributed to the first term that covers it

    result.hits.sort(key=lambda hit: hit.position)
    return result


def screen_names(names: list[str], terms: list[AllergenTerm]) -> AllergenScreen:
    """Screen a bare INCI name list, for callers without an Analysis."""
    from app.services.analysis import analyze

    return screen(analyze(names), terms)
