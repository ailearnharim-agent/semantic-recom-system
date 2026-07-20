"""
Dataset: McAuley-Lab/Amazon-Reviews-2023, Fashion metadata subset.
Streams a capped sample (SAMPLE_SIZE) instead of the full ~800k-row category.
Assumes the dataset is reachable -- fails loudly (no fallback) if it isn't.
"""
import itertools
import json
from pathlib import Path

from datasets import load_dataset

SAMPLE_SIZE = 300
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "raw_products.jsonl"


def stream_from_huggingface(n: int) -> list[dict]:
    ds = load_dataset(
        "McAuley-Lab/Amazon-Reviews-2023",
        "raw_meta_Amazon_Fashion",
        split="full",
        streaming=True,
        trust_remote_code=True,
    )
    records = []
    for row in itertools.islice(ds, n):
        records.append(
            {
                "main_category": row.get("main_category"),
                "title": row.get("title"),
                "average_rating": row.get("average_rating"),
                "rating_number": row.get("rating_number"),
                "features": row.get("features") or [],
                "description": row.get("description") or [],
                "price": row.get("price"),
                "images": row.get("images") or [],
                "videos": row.get("videos") or [],
                "store": row.get("store"),
                "categories": row.get("categories") or [],
                "details": row.get("details") or {},
                "parent_asin": row.get("parent_asin"),
                "bought_together": row.get("bought_together") or [],
            }
        )

    if not records:
        raise RuntimeError("Hugging Face stream returned zero records for raw_meta_Amazon_Fashion")
    return records


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    records = stream_from_huggingface(SAMPLE_SIZE)

    with OUT_PATH.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    print(f"[ingest] wrote {len(records)} records from Hugging Face -> {OUT_PATH}")


if __name__ == "__main__":
    main()
