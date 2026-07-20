"""
Query-time embedding service. Java calls this over HTTP instead of loading
the model in-process -- keeps the model in one place (Python), avoids
wiring ONNX/DJL into the JVM, and guarantees query embeddings and catalog
embeddings always come from the same model artifact.
"""
from fastapi import FastAPI
from pydantic import BaseModel

from embedding_model import EMBEDDING_DIM, embed_query, get_model

app = FastAPI(title="embed-service")


class EmbedRequest(BaseModel):
    text: str


class EmbedResponse(BaseModel):
    embedding: list[float]
    dim: int


@app.on_event("startup")
def _warm_model() -> None:
    get_model()  # load once at startup, not on the first request


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "dim": EMBEDDING_DIM}


@app.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest) -> EmbedResponse:
    vector = embed_query(req.text)
    return EmbedResponse(embedding=vector, dim=len(vector))
