"""Encode the catalog and upsert into Postgres/pgvector."""
import json
import os
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, execute_values

from embedding_model import EMBEDDING_DIM, embed_texts

PRODUCTS_PATH = Path(__file__).resolve().parent.parent / "data" / "products.jsonl"

# Port 5434 -- matches docker-compose.yml (5433 is the other project's container)
DB_DSN = os.environ.get(
    "DATABASE_URL",
    "postgresql://reco:reco@localhost:5434/reco",
)

DDL = f"""
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS product (
  parent_asin     TEXT PRIMARY KEY,
  title           TEXT NOT NULL,
  store           TEXT,
  main_category   TEXT,
  price           NUMERIC,
  average_rating  REAL,
  rating_number   INT,
  categories      TEXT[],
  details         JSONB,
  product_text    TEXT,
  embedding       VECTOR({EMBEDDING_DIM})
);

CREATE INDEX IF NOT EXISTS product_embedding_idx ON product
  USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS product_category_idx ON product USING GIN (categories);
"""

UPSERT_SQL = """
INSERT INTO product
  (parent_asin, title, store, main_category, price, average_rating,
   rating_number, categories, details, product_text, embedding)
VALUES %s
ON CONFLICT (parent_asin) DO UPDATE SET
  title = EXCLUDED.title,
  store = EXCLUDED.store,
  main_category = EXCLUDED.main_category,
  price = EXCLUDED.price,
  average_rating = EXCLUDED.average_rating,
  rating_number = EXCLUDED.rating_number,
  categories = EXCLUDED.categories,
  details = EXCLUDED.details,
  product_text = EXCLUDED.product_text,
  embedding = EXCLUDED.embedding;
"""


def load_products() -> list[dict]:
    with PRODUCTS_PATH.open() as f:
        return [json.loads(line) for line in f]


def main() -> None:
    products = load_products()
    print(f"[build_index] encoding {len(products)} products with bge-small-en-v1.5 ...")
    vectors = embed_texts([p["product_text"] for p in products])

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(DDL)

        rows = []
        for p, vec in zip(products, vectors):
            rows.append(
                (
                    p["parent_asin"],
                    p["title"],
                    p.get("store"),
                    p.get("main_category"),
                    p.get("price"),
                    p.get("average_rating"),
                    p.get("rating_number"),
                    p.get("categories") or [],
                    Json(p.get("details") or {}),
                    p["product_text"],
                    vec,
                )
            )
        execute_values(cur, UPSERT_SQL, rows, template="(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)")

    print(f"[build_index] upserted {len(rows)} rows into pgvector")
    conn.close()


if __name__ == "__main__":
    main()
