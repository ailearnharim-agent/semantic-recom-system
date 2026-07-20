"""
Automated retrieval-quality regression test.

Methodology caveat, stated plainly: relevance here is approximated by
keyword presence (golden_queries.py), which structurally favors the
keyword-matching baseline -- it is judged by exactly the signal it
optimizes for. Vector search beating it anyway at K=5 is the meaningful
result; a K=10 tie is not evidence of a bug. Thresholds below are set from
an actual measured run (see evaluate_retrieval.py output), not guessed,
with headroom for run-to-run noise (embedding ties, DB ordering).

Requires the pgvector container to be up and indexed (docker compose up -d
postgres && python build_index.py). Run with: pytest test_retrieval_quality.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest

from evaluate_retrieval import compute_metrics


@pytest.fixture(scope="module")
def metrics_k5():
    return compute_metrics(k=5)


def test_average_precision_at_5_meets_quality_floor(metrics_k5):
    # 0.6 leaves real headroom for catalog/model changes while still
    # catching a genuine regression.
    assert metrics_k5["avg_vector_precision"] >= 0.6


def test_vector_search_not_worse_than_keyword_baseline_beyond_noise(metrics_k5):
    # Despite the keyword-favoring methodology (see module docstring),
    # vector search should not fall meaningfully behind a naive keyword
    # baseline -- if it does, something regressed.
    assert metrics_k5["avg_vector_precision"] >= metrics_k5["avg_keyword_precision"] - 0.15


def test_every_query_returns_results(metrics_k5):
    for row in metrics_k5["rows"]:
        assert row["vector_top1_title"] is not None, f"no results for: {row['query']}"


def test_known_sparse_category_does_not_silently_regress_elsewhere(metrics_k5):
    # "hiking gear" is a documented catalog-coverage gap (6/300 products),
    # expected to score low -- this test just pins that it's the ONLY
    # near-zero query, so a future regression on a well-covered category
    # doesn't hide behind "oh, that's just the hiking one."
    near_zero = [r for r in metrics_k5["rows"] if r["vector_precision_at_k"] <= 0.2]
    near_zero_queries = {r["query"] for r in near_zero}
    assert near_zero_queries <= {"hiking gear for cold weather"}, (
        f"unexpected near-zero precision on: {near_zero_queries - {'hiking gear for cold weather'}}"
    )
