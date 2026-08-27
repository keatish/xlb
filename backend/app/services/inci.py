"""INCI list parsing and ingredient dictionary lookup.

Real ingredient lists are messy: parenthetical common names, "may contain"
tails, bullet separators, water listed five different ways. This module turns
that into an ordered list of canonical names.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from slugify import slugify

from app.services.text import normalize_text

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Same substance, different label depending on region and brand.
ALIASES: dict[str, str] = {
    "water": "Water",
    "aqua": "Water",
    "aqua water": "Water",
    "water aqua": "Water",
    "purified water": "Water",
    "distilled water": "Water",
    "parfum": "Fragrance",
    "fragrance parfum": "Fragrance",
    "parfum fragrance": "Fragrance",
    "vitamin e": "Tocopherol",
    "vitamin c": "Ascorbic Acid",
    "l ascorbic acid": "Ascorbic Acid",
    "vitamin b3": "Niacinamide",
    "nicotinamide": "Niacinamide",
    "provitamin b5": "Panthenol",
    "d panthenol": "Panthenol",
    "dl panthenol": "Panthenol",
    "centella asiatica leaf extract": "Centella Asiatica Extract",
    "centella asiatica water": "Centella Asiatica Extract",
    "green tea extract": "Camellia Sinensis Leaf Extract",
    "licorice root extract": "Glycyrrhiza Glabra Root Extract",
    "shea butter": "Butyrospermum Parkii Butter",
    "coconut oil": "Cocos Nucifera Oil",
    "jojoba oil": "Simmondsia Chinensis Seed Oil",
    "rosehip oil": "Rosa Canina Fruit Oil",
    "sunflower seed oil": "Helianthus Annuus Seed Oil",
    "argan oil": "Argania Spinosa Kernel Oil",
    "olive oil": "Olea Europaea Fruit Oil",
    "hyaluronic acid sodium salt": "Sodium Hyaluronate",
    "snail mucin": "Snail Secretion Filtrate",
    "alcohol denat": "Alcohol Denat.",
    "sd alcohol": "Alcohol Denat.",
    "denatured alcohol": "Alcohol Denat.",
    "tea tree oil": "Melaleuca Alternifolia Leaf Oil",
    "lavender oil": "Lavandula Angustifolia Oil",
    "beta glucan": "Beta-Glucan",
    "alpha arbutin": "Alpha-Arbutin",
    "ethyl ascorbic acid": "3-O-Ethyl Ascorbic Acid",
    "granactive retinoid": "Hydroxypinacolone Retinoate",
    "adenosine": "Adenosine",
}

_SPLIT_RE = re.compile(r"[,;•·•\n]|(?:\s+/\s+)")
# Some INCI names carry an internal comma - "1,2-Hexanediol", "1,3-Butylene
# Glycol". Splitting on those commas shreds the name, so they are protected
# before the split and restored after.
_NUMERIC_COMMA_RE = re.compile(r"(?<=\d),(?=\d)")
_COMMA_PLACEHOLDER = "\x00"
_MAY_CONTAIN_RE = re.compile(r"\bmay\s+contain\b.*$", re.IGNORECASE | re.DOTALL)
_PERCENT_RE = re.compile(r"\d+(?:\.\d+)?\s*%")
_LEADING_LABEL_RE = re.compile(
    r"^\s*(?:full\s+)?ingredients?\s*(?:list)?\s*[:\-]\s*", re.IGNORECASE
)


@lru_cache(maxsize=1)
def ingredient_dictionary() -> dict[str, dict]:
    """INCI name (normalized) -> dictionary entry."""
    raw = json.loads((DATA_DIR / "ingredients.json").read_text(encoding="utf-8"))
    table: dict[str, dict] = {}
    for entry in raw:
        entry = dict(entry)
        entry["slug"] = slugify(entry["inci_name"])
        table[normalize_text(entry["inci_name"])] = entry
    return table


@lru_cache(maxsize=1)
def _alias_table() -> dict[str, str]:
    return {normalize_text(k): v for k, v in ALIASES.items()}


def canonicalize(name: str) -> str:
    """Map a raw ingredient string onto a canonical INCI name where we know one."""
    cleaned = clean_ingredient_name(name)
    if not cleaned:
        return ""
    key = normalize_text(cleaned)
    alias = _alias_table().get(key)
    if alias:
        return alias
    known = ingredient_dictionary().get(key)
    if known:
        return known["inci_name"]
    return cleaned


def clean_ingredient_name(raw: str) -> str:
    """Strip percentages, parentheticals, asterisks and stray whitespace."""
    if not raw:
        return ""
    text = raw.strip()
    text = _PERCENT_RE.sub(" ", text)
    # "Butyrospermum Parkii (Shea) Butter" -> keep outer, drop the aside.
    text = re.sub(r"\(([^)]*)\)", " ", text)
    text = re.sub(r"[\[\]{}*†‡]", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" .-")
    return text


def parse_ingredients(raw: str | None) -> list[str]:
    """Turn a raw INCI blob into an ordered, de-duplicated list of names.

    Order is preserved because INCI position approximates concentration.
    """
    if not raw:
        return []

    text = _LEADING_LABEL_RE.sub("", raw.strip())
    text = _MAY_CONTAIN_RE.sub("", text)
    text = _NUMERIC_COMMA_RE.sub(_COMMA_PLACEHOLDER, text)

    names: list[str] = []
    seen: set[str] = set()
    for chunk in _SPLIT_RE.split(text):
        name = canonicalize(chunk.replace(_COMMA_PLACEHOLDER, ","))
        if not name or len(name) < 2 or len(name) > 120:
            continue
        # Reject sentences - prose slipped in from marketing copy.
        if len(name.split()) > 8:
            continue
        key = normalize_text(name)
        if key in seen:
            continue
        seen.add(key)
        names.append(name)
    return names


def normalize_name_list(names: list[str]) -> list[str]:
    """Canonicalize an already-split list (e.g. from INCIDecoder)."""
    out: list[str] = []
    seen: set[str] = set()
    for name in names:
        canonical = canonicalize(name)
        if not canonical:
            continue
        key = normalize_text(canonical)
        if key in seen:
            continue
        seen.add(key)
        out.append(canonical)
    return out


def lookup(name: str) -> dict | None:
    """Dictionary entry for a canonical name, if we know the ingredient."""
    return ingredient_dictionary().get(normalize_text(name))
