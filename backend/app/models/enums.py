import enum


class Category(str, enum.Enum):
    CLEANSER = "cleanser"
    TONER = "toner"
    ESSENCE = "essence"
    SERUM = "serum"
    MOISTURIZER = "moisturizer"
    SUNSCREEN = "sunscreen"
    MASK = "mask"
    EYE_CREAM = "eye_cream"
    EXFOLIANT = "exfoliant"
    TREATMENT = "treatment"


class SkinType(str, enum.Enum):
    DRY = "dry"
    OILY = "oily"
    COMBINATION = "combination"
    NORMAL = "normal"
    SENSITIVE = "sensitive"


class MatchMethod(str, enum.Enum):
    UPC = "upc"
    FUZZY = "fuzzy"
    MANUAL = "manual"


class ScrapeStatus(str, enum.Enum):
    OK = "ok"
    BLOCKED = "blocked"
    FAILED = "failed"
    NOT_FOUND = "not_found"


CATEGORY_LABELS: dict[str, str] = {
    "cleanser": "Cleanser",
    "toner": "Toner",
    "essence": "Essence",
    "serum": "Serum",
    "moisturizer": "Moisturizer",
    "sunscreen": "Sunscreen",
    "mask": "Mask",
    "eye_cream": "Eye Cream",
    "exfoliant": "Exfoliant",
    "treatment": "Treatment",
}
