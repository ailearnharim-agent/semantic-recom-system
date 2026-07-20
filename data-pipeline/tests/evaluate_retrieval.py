"""
Retrieval quality evaluation.

Computes Precision@K for the actual vector search (same query -> pgvector
cosine-similarity path RetrievalService.java uses) against a naive
keyword-match baseline standing in for traditional keyword search -- the
thing this whole project is supposed to improve on. No labeled relevance
judgments exist for this dataset, so relevance is approximated by keyword
rules in golden_queries.py; see that file for the coverage this was
calibrated against.

Run directly for a human-readable report:
    python evaluate_retrieval.py
Or import compute_metrics() from pytest (see test_retrieval_quality.py).
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import psycopg2

from embedding_model import embed_query
from golden_queries import GOLDEN_QUERIES

DB_DSN = os.environ.get("DATABASE_URL", "postgresql://reco:reco@localhost:5434/reco")

STOPWORDS = {
    "a", "an", "the", "for", "to", "of", "or", "and", "in", "on", "with",
    "this", "that", "is", "as", "at", "i", "me", "my", "go", "need",
}


def _tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOPWORDS]


def fetch_catalog(conn) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute("SELECT parent_asin, title, product_text FROM product")
        rows = cur.fetchall()
    return [{"parent_asin": r[0], "title": r[1], "product_text": r[2] or ""} for r in rows]


def is_relevant(product: dict, keywords: list[str]) -> bool:
    haystack = (product["title"] + " " + product["product_text"]).lower()
    return any(kw.lower() in haystack for kw in keywords)


def vector_search(conn, query: str, k: int) -> list[dict]:
    vector = embed_query(query)
    literal = "[" + ",".join(str(v) for v in vector) + "]"
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT parent_asin, title, product_text
            FROM product
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (literal, k),
        )
        rows = cur.fetchall()
    return [{"parent_asin": r[0], "title": r[1], "product_text": r[2] or ""} for r in rows]


def keyword_baseline_search(catalog: list[dict], query: str, k: int) -> list[dict]:
    """Naive TF ranking over query tokens -- stands in for classic keyword search."""
    tokens = _tokenize(query)
    scored = []
    for p in catalog:
        haystack = (p["title"] + " " + p["product_text"]).lower()
        score = sum(haystack.count(t) for t in tokens)
        scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for score, p in scored[:k] if score > 0] or [p for _, p in scored[:k]]


def precision_at_k(results: list[dict], keywords: list[str]) -> float:
    if not results:
        return 0.0
    hits = sum(1 for r in results if is_relevant(r, keywords))
    return hits / len(results)


def compute_metrics(k: int = 5) -> dict:
    conn = psycopg2.connect(DB_DSN)
    catalog = fetch_catalog(conn)

    rows = []
    for gq in GOLDEN_QUERIES:
        vec_results = vector_search(conn, gq["query"], k)
        kw_results = keyword_baseline_search(catalog, gq["query"], k)

        vec_p = precision_at_k(vec_results, gq["keywords"])
        kw_p = precision_at_k(kw_results, gq["keywords"])

        rows.append(
            {
                "query": gq["query"],
                "catalog_matches": gq["catalog_matches"],
                "vector_precision_at_k": vec_p,
                "keyword_precision_at_k": kw_p,
                "vector_top1_title": vec_results[0]["title"] if vec_results else None,
            }
        )

    conn.close()

    avg_vector = sum(r["vector_precision_at_k"] for r in rows) / len(rows)
    avg_keyword = sum(r["keyword_precision_at_k"] for r in rows) / len(rows)

    return {"k": k, "rows": rows, "avg_vector_precision": avg_vector, "avg_keyword_precision": avg_keyword}


def print_report(metrics: dict) -> None:
    k = metrics["k"]
    print(f"\nRetrieval quality report -- Precision@{k}\n" + "=" * 72)
    print(f"{'query':<45} {'vector':>8} {'keyword':>8} {'catalog':>8}")
    print("-" * 72)
    for r in metrics["rows"]:
        print(
            f"{r['query'][:44]:<45} {r['vector_precision_at_k']:>8.2f} "
            f"{r['keyword_precision_at_k']:>8.2f} {r['catalog_matches']:>8}"
        )
    print("-" * 72)
    print(
        f"{'AVERAGE':<45} {metrics['avg_vector_precision']:>8.2f} "
        f"{metrics['avg_keyword_precision']:>8.2f}"
    )
    lift = metrics["avg_vector_precision"] - metrics["avg_keyword_precision"]
    print(f"\nVector search vs. keyword baseline: {lift:+.2f} precision @ {k}")


if __name__ == "__main__":
    print_report(compute_metrics(k=5))
    print_report(compute_metrics(k=10))
