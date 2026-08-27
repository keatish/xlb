"""Synthetic product catalog for local development.

These are plausible skincare products with realistic INCI lists built from the
ingredient dictionary, so the analysis, dupe and conflict features have genuine
signal to work with rather than placeholder noise.

Formulas are representative, not transcriptions of any real product's label -
this is development seed data, not a reference for what is actually in a given
bottle. Real ingredient data comes from the ingestion pipeline.

Each entry: (brand, name, category, size_value, size_unit, base_price, concerns,
ingredients-in-INCI-order).
"""

from __future__ import annotations

# Shared bases, so products in the same family look genuinely alike to the dupe
# finder - which is the behaviour we want to be able to demonstrate.
HYDRATING_BASE = ["Water", "Glycerin", "Butylene Glycol", "1,2-Hexanediol"]
CREAM_BASE = [
    "Water", "Glycerin", "Caprylic/Capric Triglyceride", "Cetearyl Alcohol",
    "Glyceryl Stearate", "Dimethicone",
]
PRESERVATIVES = ["Phenoxyethanol", "Ethylhexylglycerin", "Disodium EDTA"]
GEL_TEXTURE = ["Xanthan Gum", "Carbomer", "Sodium Hydroxide"]

SEED_PRODUCTS: list[tuple] = [
    # ---------------------------------------------------------------- cleansers
    (
        "CeraVe", "Hydrating Facial Cleanser", "cleanser", 355.0, "ml", 16.99,
        {"dryness": 1.0, "barrier": 0.9},
        HYDRATING_BASE + ["Cocamidopropyl Betaine", "Ceramide NP", "Ceramide AP",
                          "Ceramide EOP", "Cholesterol", "Hyaluronic Acid",
                          "Phytosphingosine"] + PRESERVATIVES,
    ),
    (
        "COSRX", "Low pH Good Morning Gel Cleanser", "cleanser", 150.0, "ml", 13.00,
        {"acne": 0.8, "oiliness": 0.7, "barrier": 0.6},
        HYDRATING_BASE + ["Cocamidopropyl Betaine", "Coco-Glucoside",
                          "Betaine Salicylate", "Centella Asiatica Extract",
                          "Allantoin", "Panthenol"] + PRESERVATIVES,
    ),
    (
        "Vanicream", "Gentle Facial Cleanser", "cleanser", 237.0, "ml", 9.99,
        {"redness": 1.0, "barrier": 0.8},
        HYDRATING_BASE + ["Decyl Glucoside", "Coco-Glucoside", "Panthenol",
                          "Allantoin", "Sodium PCA"] + PRESERVATIVES,
    ),
    (
        "Anua", "Heartleaf Quercetinol Pore Deep Cleansing Foam", "cleanser", 150.0, "ml", 18.00,
        {"acne": 0.8, "oiliness": 0.9, "texture": 0.6},
        HYDRATING_BASE + ["Potassium Cocoyl Glycinate", "Cocamidopropyl Betaine",
                          "Salicylic Acid", "Centella Asiatica Extract",
                          "Zinc PCA", "Panthenol"] + PRESERVATIVES,
    ),
    (
        "Beauty of Joseon", "Green Plum Refreshing Cleanser", "cleanser", 150.0, "ml", 14.00,
        {"oiliness": 0.7, "texture": 0.6},
        HYDRATING_BASE + ["Coco-Glucoside", "Cocamidopropyl Betaine",
                          "Lactic Acid", "Camellia Sinensis Leaf Extract",
                          "Niacinamide"] + PRESERVATIVES,
    ),

    # ------------------------------------------------------------------- toners
    (
        "Anua", "Heartleaf 77% Soothing Toner", "toner", 250.0, "ml", 21.00,
        {"redness": 1.0, "barrier": 0.8, "acne": 0.5},
        ["Water", "Centella Asiatica Extract", "Glycerin", "Butylene Glycol",
         "1,2-Hexanediol", "Panthenol", "Allantoin", "Madecassoside",
         "Beta-Glucan", "Sodium Hyaluronate"] + PRESERVATIVES,
    ),
    (
        "Isntree", "Hyaluronic Acid Toner", "toner", 200.0, "ml", 22.00,
        {"dryness": 1.0, "barrier": 0.7},
        HYDRATING_BASE + ["Sodium Hyaluronate", "Hydrolyzed Hyaluronic Acid",
                          "Sodium Acetylated Hyaluronate", "Betaine",
                          "Panthenol", "Allantoin", "Trehalose"] + PRESERVATIVES,
    ),
    (
        "Round Lab", "1025 Dokdo Toner", "toner", 200.0, "ml", 19.00,
        {"dryness": 0.8, "redness": 0.7, "barrier": 0.7},
        HYDRATING_BASE + ["Betaine", "Panthenol", "Allantoin", "Beta-Glucan",
                          "Sodium Hyaluronate", "Centella Asiatica Extract"] + PRESERVATIVES,
    ),
    (
        "Paula's Choice", "Skin Perfecting 2% BHA Liquid Exfoliant", "exfoliant", 118.0, "ml", 35.00,
        {"acne": 1.0, "texture": 0.9, "oiliness": 0.8, "dark_spots": 0.5},
        ["Water", "Butylene Glycol", "Salicylic Acid", "Camellia Sinensis Leaf Extract",
         "Sodium Hydroxide", "Tetrasodium EDTA"] + ["Glycerin"],
    ),
    (
        "The Ordinary", "Glycolic Acid 7% Exfoliating Toner", "exfoliant", 240.0, "ml", 13.00,
        {"texture": 1.0, "dullness": 0.9, "dark_spots": 0.7},
        ["Water", "Glycolic Acid", "Rosa Canina Fruit Oil", "Centella Asiatica Extract",
         "Camellia Sinensis Leaf Extract", "Glycerin", "Sodium Hydroxide",
         "Panthenol", "Allantoin"] + PRESERVATIVES,
    ),
    (
        "SKIN1004", "Madagascar Centella Poremizing Deep Cleansing Foam", "exfoliant", 100.0, "ml", 17.00,
        {"texture": 0.8, "acne": 0.8, "oiliness": 0.7},
        HYDRATING_BASE + ["Salicylic Acid", "Lactic Acid", "Centella Asiatica Extract",
                          "Madecassoside", "Panthenol"] + PRESERVATIVES,
    ),

    # ------------------------------------------------------------------ essence
    (
        "COSRX", "Advanced Snail 96 Mucin Power Essence", "essence", 100.0, "ml", 19.00,
        {"barrier": 1.0, "dryness": 0.8, "dark_spots": 0.4},
        ["Snail Secretion Filtrate", "Betaine", "Butylene Glycol", "1,2-Hexanediol",
         "Sodium Polyacrylate", "Phenoxyethanol", "Sodium Hyaluronate",
         "Allantoin", "Panthenol", "Carbomer"],
    ),
    (
        "Mixsoon", "Bean Essence", "essence", 100.0, "ml", 24.00,
        {"texture": 0.8, "dullness": 0.7, "barrier": 0.6},
        HYDRATING_BASE + ["Lactobacillus Ferment", "Beta-Glucan", "Panthenol",
                          "Allantoin", "Sodium Hyaluronate"] + PRESERVATIVES,
    ),
    (
        "Numbuzin", "No.3 Skin Softening Serum", "essence", 200.0, "ml", 27.00,
        {"dullness": 0.9, "texture": 0.7, "dryness": 0.6},
        HYDRATING_BASE + ["Saccharomyces Ferment Filtrate", "Bifida Ferment Lysate",
                          "Niacinamide", "Panthenol", "Beta-Glucan"] + PRESERVATIVES,
    ),

    # ------------------------------------------------------------------- serums
    (
        "The Ordinary", "Niacinamide 10% + Zinc 1%", "serum", 30.0, "ml", 6.50,
        {"oiliness": 1.0, "acne": 0.8, "dark_spots": 0.6, "texture": 0.5},
        ["Water", "Niacinamide", "Pentylene Glycol", "Zinc PCA", "Xanthan Gum",
         "Isoceteth-20", "Phenoxyethanol", "Chlorphenesin"],
    ),
    (
        "Good Molecules", "Niacinamide Serum", "serum", 30.0, "ml", 6.00,
        {"oiliness": 0.9, "acne": 0.7, "dark_spots": 0.5},
        ["Water", "Niacinamide", "Propanediol", "Zinc PCA", "Glycerin",
         "Xanthan Gum"] + PRESERVATIVES,
    ),
    (
        "The Inkey List", "Niacinamide Serum", "serum", 30.0, "ml", 8.99,
        {"oiliness": 0.9, "acne": 0.7, "redness": 0.4},
        ["Water", "Niacinamide", "Butylene Glycol", "Zinc PCA", "Glycerin",
         "Allantoin", "Xanthan Gum"] + PRESERVATIVES,
    ),
    (
        "Beauty of Joseon", "Glow Serum Propolis + Niacinamide", "serum", 30.0, "ml", 17.00,
        {"dullness": 0.9, "barrier": 0.7, "acne": 0.5},
        ["Water", "Propolis Extract", "Niacinamide", "Butylene Glycol", "Glycerin",
         "Panthenol", "Allantoin", "Beta-Glucan", "Sodium Hyaluronate"] + PRESERVATIVES,
    ),
    (
        "The Ordinary", "Vitamin C Suspension 23% + HA Spheres 2%", "serum", 30.0, "ml", 7.50,
        {"dullness": 1.0, "dark_spots": 0.9, "aging": 0.6},
        ["Ascorbic Acid", "Squalane", "Isodecyl Neopentanoate",
         "Isononyl Isononanoate", "Ethylene/Propylene/Styrene Copolymer",
         "Sodium Hyaluronate"],
    ),
    (
        "Timeless", "20% Vitamin C + E Ferulic Acid Serum", "serum", 30.0, "ml", 25.00,
        {"dullness": 1.0, "dark_spots": 0.9, "aging": 0.8},
        ["Water", "Ascorbic Acid", "Propanediol", "Tocopherol", "Ferulic Acid",
         "Panthenol", "Sodium Hyaluronate"] + PRESERVATIVES,
    ),
    (
        "Naturium", "Vitamin C Complex Serum", "serum", 30.0, "ml", 20.00,
        {"dullness": 0.9, "dark_spots": 0.8, "aging": 0.6},
        HYDRATING_BASE + ["3-O-Ethyl Ascorbic Acid", "Tetrahexyldecyl Ascorbate",
                          "Ferulic Acid", "Tocopherol", "Niacinamide",
                          "Squalane"] + PRESERVATIVES,
    ),
    (
        "The Ordinary", "Alpha Arbutin 2% + HA", "serum", 30.0, "ml", 9.00,
        {"dark_spots": 1.0, "dullness": 0.6},
        ["Water", "Alpha-Arbutin", "Propanediol", "Sodium Hyaluronate",
         "Xanthan Gum"] + PRESERVATIVES,
    ),
    (
        "SKIN1004", "Madagascar Centella Ampoule", "serum", 100.0, "ml", 18.00,
        {"redness": 1.0, "barrier": 0.9},
        ["Centella Asiatica Extract", "Water", "Glycerin", "Butylene Glycol",
         "Madecassoside", "Asiaticoside", "Madecassic Acid", "Asiatic Acid",
         "Panthenol", "Allantoin"] + PRESERVATIVES,
    ),
    (
        "Torriden", "DIVE-IN Low Molecular Hyaluronic Acid Serum", "serum", 50.0, "ml", 19.00,
        {"dryness": 1.0, "barrier": 0.8},
        HYDRATING_BASE + ["Sodium Hyaluronate", "Hydrolyzed Hyaluronic Acid",
                          "Panthenol", "Allantoin", "Beta-Glucan",
                          "Centella Asiatica Extract"] + PRESERVATIVES,
    ),
    (
        "The Ordinary", "Granactive Retinoid 2% Emulsion", "treatment", 30.0, "ml", 11.00,
        {"aging": 1.0, "texture": 0.8, "acne": 0.6},
        ["Water", "Hydroxypinacolone Retinoate", "Caprylic/Capric Triglyceride",
         "Glycerin", "Dimethicone", "Squalane", "Tocopherol"] + PRESERVATIVES,
    ),
    (
        "Geek & Gorgeous", "A-Game 5 Retinal Serum", "treatment", 30.0, "ml", 16.00,
        {"aging": 1.0, "texture": 0.9, "dark_spots": 0.6},
        ["Water", "Glycerin", "Retinal", "Squalane", "Niacinamide", "Panthenol",
         "Tocopherol", "Allantoin"] + PRESERVATIVES,
    ),
    (
        "Paula's Choice", "10% Azelaic Acid Booster", "treatment", 30.0, "ml", 42.00,
        {"redness": 1.0, "acne": 0.9, "dark_spots": 0.8},
        ["Water", "Azelaic Acid", "Glycerin", "Dimethicone", "Niacinamide",
         "Allantoin", "Bisabolol", "Squalane"] + PRESERVATIVES,
    ),
    (
        "Differin", "Adapalene Gel 0.1%", "treatment", 45.0, "g", 14.99,
        {"acne": 1.0, "texture": 0.7},
        ["Water", "Adapalene", "Carbomer", "Propylene Glycol",
         "Sodium Hydroxide", "Disodium EDTA", "Phenoxyethanol"],
    ),

    # -------------------------------------------------------------- moisturizers
    (
        "CeraVe", "Moisturizing Cream", "moisturizer", 454.0, "g", 18.99,
        {"dryness": 1.0, "barrier": 1.0},
        CREAM_BASE + ["Petrolatum", "Ceramide NP", "Ceramide AP", "Ceramide EOP",
                      "Cholesterol", "Hyaluronic Acid", "Phytosphingosine",
                      "Panthenol"] + PRESERVATIVES,
    ),
    (
        "COSRX", "Advanced Snail 92 All In One Cream", "moisturizer", 100.0, "ml", 21.90,
        {"barrier": 1.0, "dryness": 0.9},
        ["Snail Secretion Filtrate", "Water", "Glycerin", "Caprylic/Capric Triglyceride",
         "Cetearyl Alcohol", "Dimethicone", "Panthenol", "Allantoin",
         "Sodium Hyaluronate", "Betaine"] + PRESERVATIVES,
    ),
    (
        "Illiyoon", "Ceramide Ato Concentrate Cream", "moisturizer", 200.0, "ml", 17.00,
        {"dryness": 1.0, "barrier": 1.0, "redness": 0.6},
        CREAM_BASE + ["Ceramide NP", "Cholesterol", "Panthenol", "Allantoin",
                      "Beta-Glucan", "Colloidal Oatmeal"] + PRESERVATIVES,
    ),
    (
        "Laneige", "Water Bank Blue Hyaluronic Cream", "moisturizer", 50.0, "ml", 38.00,
        {"dryness": 1.0, "barrier": 0.7},
        CREAM_BASE + ["Sodium Hyaluronate", "Hydrolyzed Hyaluronic Acid",
                      "Squalane", "Panthenol", "Trehalose", "Fragrance"] + PRESERVATIVES,
    ),
    (
        "Vanicream", "Moisturizing Cream", "moisturizer", 453.0, "g", 13.99,
        {"dryness": 1.0, "redness": 0.9, "barrier": 0.9},
        ["Water", "Petrolatum", "Cetearyl Alcohol", "Glycerin", "Squalane",
         "Sodium Hyaluronate", "Panthenol", "Allantoin"] + PRESERVATIVES,
    ),
    (
        "Purito", "Dermide Cica Barrier Cream", "moisturizer", 80.0, "ml", 22.00,
        {"barrier": 1.0, "redness": 0.9, "dryness": 0.7},
        CREAM_BASE + ["Ceramide NP", "Centella Asiatica Extract", "Madecassoside",
                      "Panthenol", "Beta-Glucan", "Cholesterol"] + PRESERVATIVES,
    ),
    (
        "Belif", "The True Cream Aqua Bomb", "moisturizer", 50.0, "ml", 42.00,
        {"dryness": 0.8, "oiliness": 0.5},
        HYDRATING_BASE + GEL_TEXTURE + ["Squalane", "Panthenol", "Beta-Glucan",
                                        "Fragrance", "Limonene", "Linalool"] + PRESERVATIVES,
    ),

    # ---------------------------------------------------------------- sunscreens
    (
        "Beauty of Joseon", "Relief Sun: Rice + Probiotics SPF50+", "sunscreen", 50.0, "ml", 18.00,
        {"aging": 0.8, "dark_spots": 0.7, "dryness": 0.5},
        ["Water", "Tinosorb S", "Uvinul A Plus", "Ethylhexyl Triazone", "Glycerin",
         "Oryza Sativa Extract", "Niacinamide", "Panthenol", "Squalane",
         "Centella Asiatica Extract"] + PRESERVATIVES,
    ),
    (
        "Round Lab", "Birch Juice Moisturizing Sunscreen SPF50+", "sunscreen", 50.0, "ml", 20.00,
        {"dryness": 0.8, "aging": 0.7},
        ["Water", "Tinosorb S", "Ethylhexyl Triazone", "Uvinul A Plus", "Glycerin",
         "Butylene Glycol", "Panthenol", "Sodium Hyaluronate",
         "Allantoin"] + PRESERVATIVES,
    ),
    (
        "La Roche-Posay", "Anthelios Melt-In Milk SPF 60", "sunscreen", 90.0, "ml", 36.99,
        {"aging": 0.8, "dark_spots": 0.6},
        ["Water", "Homosalate", "Avobenzone", "Octocrylene", "Glycerin",
         "Dimethicone", "Tocopherol", "Fragrance"] + PRESERVATIVES,
    ),
    (
        "SKIN1004", "Madagascar Centella Air-Fit Suncream Plus", "sunscreen", 50.0, "ml", 19.00,
        {"redness": 0.8, "aging": 0.7},
        ["Water", "Zinc Oxide", "Titanium Dioxide", "Centella Asiatica Extract",
         "Glycerin", "Squalane", "Niacinamide", "Panthenol",
         "Madecassoside"] + PRESERVATIVES,
    ),

    # --------------------------------------------------------------- eye creams
    (
        "COSRX", "Advanced Snail Peptide Eye Cream", "eye_cream", 25.0, "ml", 26.00,
        {"aging": 0.9, "dryness": 0.7},
        ["Snail Secretion Filtrate", "Water", "Glycerin", "Palmitoyl Tripeptide-1",
         "Palmitoyl Tetrapeptide-7", "Adenosine", "Niacinamide", "Panthenol",
         "Squalane"] + PRESERVATIVES,
    ),
    (
        "The Inkey List", "Caffeine Eye Cream", "eye_cream", 15.0, "ml", 9.99,
        {"aging": 0.6, "dullness": 0.5},
        HYDRATING_BASE + ["Caffeine", "Palmitoyl Tripeptide-1", "Squalane",
                          "Panthenol", "Tocopherol"] + PRESERVATIVES,
    ),

    # -------------------------------------------------------------------- masks
    (
        "Laneige", "Water Sleeping Mask", "mask", 70.0, "ml", 26.00,
        {"dryness": 1.0, "dullness": 0.6},
        HYDRATING_BASE + GEL_TEXTURE + ["Sodium Hyaluronate", "Trehalose",
                                        "Squalane", "Panthenol", "Fragrance",
                                        "Limonene"] + PRESERVATIVES,
    ),
    (
        "Beauty of Joseon", "Revive Eye Serum Ginseng + Retinal", "treatment", 30.0, "ml", 17.00,
        {"aging": 1.0, "dark_spots": 0.6},
        ["Water", "Panax Ginseng Root Extract", "Retinal", "Glycerin", "Squalane",
         "Niacinamide", "Adenosine", "Panthenol", "Tocopherol"] + PRESERVATIVES,
    ),
    (
        "Some By Mi", "AHA BHA PHA 30 Days Miracle Toner", "exfoliant", 150.0, "ml", 16.00,
        {"acne": 1.0, "texture": 0.9, "oiliness": 0.7},
        ["Water", "Lactic Acid", "Salicylic Acid", "Gluconolactone", "Glycerin",
         "Butylene Glycol", "Niacinamide", "Centella Asiatica Extract",
         "Melaleuca Alternifolia Leaf Oil", "Allantoin"] + PRESERVATIVES,
    ),
]


# Retailers used for seed listings. Names are generic on purpose - this is
# synthetic data and should not be read as real pricing from a real store.
SEED_RETAILERS: list[tuple[str, str, str]] = [
    ("GlowMart", "glowmart", "https://example.com/glowmart"),
    ("K-Beauty Depot", "kbeauty-depot", "https://example.com/kbeauty-depot"),
    ("DermaShop", "dermashop", "https://example.com/dermashop"),
    ("BeautyBazaar", "beautybazaar", "https://example.com/beautybazaar"),
]
