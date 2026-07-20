"""
Golden evaluation set for retrieval quality.

No official relevance judgments exist for this dataset, so each query carries
a hand-written relevance rule (keywords whose presence in a product's text
counts that product as relevant) grounded in an actual keyword census of the
indexed 300-product sample -- run this to verify the counts haven't drifted:

    SELECT count(*) FILTER (WHERE product_text ILIKE '%beach%') FROM product;

Coverage is intentionally mixed: most queries hit categories with 20-150
matching products (dresses, tops, jewelry are common in this sample), a few
hit sparse categories (hiking gear: 6 matches in 300 products) on purpose --
an honest eval set has to include queries the system CAN'T do well on, or it
isn't measuring anything.
"""

GOLDEN_QUERIES = [
    {
        "query": "an outfit to go to the beach this summer",
        "keywords": ["beach", "swim", "summer", "cover up", "cooler", "tote"],
        "catalog_matches": 14,
    },
    {
        "query": "warm winter jacket or coat",
        "keywords": ["winter", "jacket", "coat", "fleece", "fur", "puffer"],
        "catalog_matches": 23,
    },
    {
        "query": "elegant dress for a summer wedding",
        "keywords": ["dress", "wedding", "formal", "elegant", "gown"],
        "catalog_matches": 51,
    },
    {
        "query": "comfortable casual t-shirt",
        "keywords": ["shirt", "tee", "top", "tunic"],
        "catalog_matches": 78,
    },
    {
        "query": "jeans or casual pants",
        "keywords": ["pant", "jean", "short", "legging", "trouser"],
        "catalog_matches": 45,
    },
    {
        "query": "sneakers or boots",
        "keywords": ["shoe", "sneaker", "boot", "sandal"],
        "catalog_matches": 19,
    },
    {
        "query": "a warm hat or beanie",
        "keywords": ["hat", "cap", "beanie"],
        "catalog_matches": 28,
    },
    {
        "query": "clothing for a toddler or young child",
        "keywords": ["kid", "boy", "girl", "toddler", "infant"],
        "catalog_matches": 30,
    },
    {
        "query": "a necklace or jewelry as a gift",
        "keywords": ["jewelry", "necklace", "bracelet", "ring", "pendant"],
        "catalog_matches": 63,
    },
    {
        "query": "a tote bag or backpack",
        "keywords": ["bag", "purse", "backpack", "tote"],
        "catalog_matches": 11,
    },
    {
        "query": "yoga or workout leggings",
        "keywords": ["yoga", "athletic", "gym", "running", "legging", "workout"],
        "catalog_matches": 25,
    },
    {
        "query": "cozy socks",
        "keywords": ["sock"],
        "catalog_matches": 10,
    },
    {
        "query": "sunglasses for summer",
        "keywords": ["sunglass", "sun glass"],
        "catalog_matches": 9,
    },
    {
        "query": "hiking gear for cold weather",
        # Sparse on purpose -- only 6/300 products mention hiking at all.
        # A good system should still surface its best (imperfect) matches;
        # low precision here is a known, documented catalog-coverage limit,
        # not something the eval should silently hide.
        "keywords": ["hik", "trail", "outdoor", "trek"],
        "catalog_matches": 6,
    },
    {
        "query": "swimwear for a beach vacation",
        "keywords": ["swim", "beach", "bikini", "trunks"],
        "catalog_matches": 14,
    },
]
