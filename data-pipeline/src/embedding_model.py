"""
Shared embedding model wrapper. build_index.py (catalog) and embed_service.py
(query-time) both import from here -- using the exact same model config in
both places is not optional: cosine similarity is only meaningful if the
query vector and the catalog vectors come from the same model.

bge-small-en-v1.5, self-hosted and pretrained (not fine-tuned in this build --
that's a documented next step, not an oversight). 384-dim output.
"""
from functools import lru_cache

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384


@lru_cache(maxsize=1)
def get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
