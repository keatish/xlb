"""Curated brand list.

Chosen because each is genuinely carried by MULTIPLE retailers - price comparison
has no value for a brand sold in exactly one place. Retailer-exclusive brands are
deliberately absent.
"""

# Western drugstore / dermatologist brands
WESTERN_DRUGSTORE = [
    "CeraVe",
    "La Roche-Posay",
    "Neutrogena",
    "Eucerin",
    "Vanicream",
    "Cetaphil",
    "Aveeno",
    "Olay",
    "Differin",
    "Bioderma",
    "Avene",
    "Vichy",
]

# Affordable "ingredient-forward" brands
INGREDIENT_FORWARD = [
    "The Ordinary",
    "Paula's Choice",
    "The Inkey List",
    "Good Molecules",
    "Naturium",
    "Versed",
    "Geek & Gorgeous",
]

# K-beauty / J-beauty
ASIAN_BEAUTY = [
    "Beauty of Joseon",
    "COSRX",
    "Anua",
    "Round Lab",
    "SKIN1004",
    "Laneige",
    "Innisfree",
    "Etude House",
    "Dr. Jart+",
    "Missha",
    "Purito",
    "Isntree",
    "Torriden",
    "Mixsoon",
    "Numbuzin",
    "Medicube",
    "Some By Mi",
    "Hada Labo",
    "Biore",
    "Rohto Melano CC",
    "Klairs",
    "Benton",
    "Pyunkang Yul",
]

# Mid / prestige
PRESTIGE = [
    "Glow Recipe",
    "Drunk Elephant",
    "Tatcha",
    "Sunday Riley",
    "Kiehl's",
    "Fresh",
    "Farmacy",
    "Youth To The People",
    "First Aid Beauty",
    "Summer Fridays",
]

BRANDS: list[str] = (
    WESTERN_DRUGSTORE + INGREDIENT_FORWARD + ASIAN_BEAUTY + PRESTIGE
)

# Brands to try first during ingestion - highest cross-retailer overlap, so they
# actually produce comparable prices rather than orphan listings.
PRIORITY_BRANDS: list[str] = [
    "CeraVe",
    "The Ordinary",
    "La Roche-Posay",
    "Beauty of Joseon",
    "COSRX",
    "Anua",
    "Laneige",
    "Round Lab",
    "SKIN1004",
    "Neutrogena",
    "Paula's Choice",
    "Vanicream",
    "Cetaphil",
    "Purito",
    "Isntree",
]
