
"""
Preprocessing decisions, each traced to a specific EDA finding (notebooks/01_exploration.ipynb):

- price arrives as a string, either "None" (literal) or a numeric string
  -> must parse safely, treating "None"/"" as missing, not crash on float("None")
- details arrives as a JSON-encoded string, not a dict
  -> must json.loads() before .get(), with a fallback to {} if parsing fails
- categories is empty in 100% of this sample
  -> product_text leans on title/features/description; no category filtering built
  -> included in the template anyway (conditionally) in case a fuller pull has real data
- features/description are absent close to half the time
  -> product_text must degrade gracefully when either is missing, not require both
"""
import json
import re
from pathlib import Path

RAW_PATH = Path(__file__).resolve().parent.parent / "data" / "raw_products.jsonl"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "products.jsonl"

_HTML_TAG = re.compile(r"<[^>]+>")


def strip_html(text: str) -> str:
    return _HTML_TAG.sub(" ", text or "").strip()


def join_text(parts) -> str:
    if isinstance(parts, list):
        return " ".join(strip_html(p) for p in parts if p)
    return strip_html(parts or "")


def parse_details(details) -> dict:
    """details arrives as a JSON string in this dataset -- confirmed via EDA cell 7."""
    if isinstance(details, dict):
        return details
    if isinstance(details, str) and details.strip():
        try:
            return json.loads(details)
        except json.JSONDecodeError:
            return {}
    return {}


def normalize_price(value) -> float | None:
    """price arrives as a string, sometimes the literal text "None" -- confirmed via EDA cell 6."""
    if value is None or value == "None" or value == "":
        return None
    try:
        return round(float(value), 2)
    except (ValueError, TypeError):
        return None


def build_product_text(record: dict) -> str:
    title = record.get("title") or ""
    features = join_text(record.get("features"))
    description = join_text(record.get("description"))
    categories = " > ".join(record.get("categories") or [])  # usually empty -- see EDA
    details = parse_details(record.get("details"))
    record["details"] = details  # normalize in place so downstream code gets a real dict
    brand = details.get("Brand") or record.get("store") or ""
    material = details.get("Material") or ""
    sizes = details.get("Sizes") or []
    sizes_str = ", ".join(sizes) if isinstance(sizes, list) else str(sizes)

    parts = [
        title + ".",
        f"Brand: {brand}." if brand else "",
        f"Category: {categories}." if categories else "",  # rarely fires in this sample
        features,
        description,
        f"Material: {material}." if material else "",
        f"Available sizes: {sizes_str}." if sizes_str else "",
    ]
    return " ".join(p for p in parts if p).strip()


def main() -> None:
    seen_asins = set()
    out_records = []

    with RAW_PATH.open() as f:
        for line in f:
            record = json.loads(line)
            asin = record.get("parent_asin")
            if not asin or asin in seen_asins:
                continue
            if not record.get("title"):
                continue
            seen_asins.add(asin)

            record["price"] = normalize_price(record.get("price"))
            record["product_text"] = build_product_text(record)
            out_records.append(record)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        for r in out_records:
            f.write(json.dumps(r) + "\n")

    print(f"[preprocess] {len(out_records)} unique products -> {OUT_PATH}")


if __name__ == "__main__":
    main()
