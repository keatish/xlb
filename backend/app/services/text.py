"""Normalization helpers shared by scrapers and the matcher.

Size normalization matters more than it looks: `1.7 fl oz` and `50ml` are the same
product, and if we cannot tell that, the matcher will either miss real matches or
merge a travel size with a full size and show a wrong price.
"""

from __future__ import annotations

import re
import unicodedata

# Volume units normalized to millilitres, weight units to grams. We keep the two
# families separate - 50ml of essence and 50g of cream are not interchangeable.
ML_PER = {
    "ml": 1.0,
    "milliliter": 1.0,
    "millilitre": 1.0,
    "cc": 1.0,
    "l": 1000.0,
    "liter": 1000.0,
    "litre": 1000.0,
    "floz": 29.5735,
    "flozus": 29.5735,
    "fluidounce": 29.5735,
}
G_PER = {
    "g": 1.0,
    "gram": 1.0,
    "gr": 1.0,
    "kg": 1000.0,
    "mg": 0.001,
    "oz": 28.3495,
    "ounce": 28.3495,
    "lb": 453.592,
}

_SIZE_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*"
    r"(fl\.?\s*oz|fluid\s*ounce[s]?|ml|milli\s*lit(?:er|re)s?|cc|l\b|lit(?:er|re)s?|"
    r"g\b|grams?|gr\b|kg|mg|oz|ounces?|lb)",
    re.IGNORECASE,
)

# Marketing noise that carries no identity - stripped before fuzzy comparison.
NOISE_WORDS = {
    "new", "improved", "official", "authentic", "genuine", "korean", "korea",
    "kbeauty", "k", "beauty", "free", "shipping", "gift", "set", "pack",
    "value", "exclusive", "limited", "edition", "bestseller", "best", "seller",
    "renewal", "renewed", "ver", "version", "us", "usa", "intl", "international",
}

_PACK_RE = re.compile(r"\b(\d+)\s*(?:x|pcs?|pieces?|count|ct|pack)\b", re.IGNORECASE)


def strip_accents(value: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c)
    )


def normalize_text(value: str | None) -> str:
    """Lowercase, de-accent, strip punctuation. The base for all comparisons."""
    if not value:
        return ""
    value = strip_accents(value.lower())
    value = re.sub(r"[‘’“”]", "", value)
    value = re.sub(r"[^a-z0-9.+%\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_brand(value: str | None) -> str:
    """Brand names vary wildly between retailers - 'Dr. Jart+' vs 'DR JART'."""
    text = normalize_text(value)
    text = re.sub(r"\b(co|inc|ltd|cosmetics?|laborator(?:y|ies)|official\s*store)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_size(text: str | None) -> tuple[float | None, str | None]:
    """Pull a size out of free text.

    Returns the value in its canonical unit family: millilitres as 'ml', weight as
    'g'. Returns (None, None) when no size is present, which the matcher treats as
    'unknown' rather than 'no size'.
    """
    if not text:
        return None, None

    match = _SIZE_RE.search(text)
    if not match:
        return None, None

    raw_value = float(match.group(1).replace(",", "."))
    unit = re.sub(r"[\s.]", "", match.group(2).lower())

    if unit in ML_PER:
        return round(raw_value * ML_PER[unit], 2), "ml"
    if unit in G_PER:
        return round(raw_value * G_PER[unit], 2), "g"
    return None, None


def parse_pack_count(text: str | None) -> int:
    """Detect multipacks. A 10-pack of sheet masks is not the same SKU as one."""
    if not text:
        return 1
    match = _PACK_RE.search(text)
    if match:
        try:
            count = int(match.group(1))
            return count if 1 <= count <= 200 else 1
        except ValueError:
            return 1
    return 1


def sizes_match(
    a_value: float | None,
    a_unit: str | None,
    b_value: float | None,
    b_unit: str | None,
    tolerance: float = 0.06,
) -> bool:
    """Do two sizes refer to the same amount?

    Unknown on either side is permissive (returns True) - many listings omit size,
    and refusing to match those would lose most of the catalog. Known-but-different
    is a hard no, which is the case that actually prevents wrong prices.
    """
    if a_value is None or b_value is None:
        return True
    if a_unit != b_unit:
        # ml vs g across a water-based product is close enough to allow, but we
        # only do that when the numbers are already near-identical.
        return abs(a_value - b_value) / max(a_value, b_value) <= 0.02
    if max(a_value, b_value) == 0:
        return True
    return abs(a_value - b_value) / max(a_value, b_value) <= tolerance


def clean_product_name(title: str, brand: str | None = None) -> str:
    """Strip the brand, size and marketing noise, leaving the product identity."""
    text = normalize_text(title)

    if brand:
        brand_norm = normalize_brand(brand)
        if brand_norm and text.startswith(brand_norm):
            text = text[len(brand_norm):]
        elif brand_norm:
            text = text.replace(brand_norm, " ")

    text = _SIZE_RE.sub(" ", text)
    text = _PACK_RE.sub(" ", text)
    tokens = [t for t in text.split() if t and t not in NOISE_WORDS]
    return " ".join(tokens).strip()


def parse_price(value) -> float | None:
    """Prices arrive as '$18.00', '18,00', 1800 (cents), or already as a float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"[^\d.,]", "", text)
    if not text:
        return None
    # European style: 1.234,56 -> 1234.56
    if "," in text and "." in text and text.rindex(",") > text.rindex("."):
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None
