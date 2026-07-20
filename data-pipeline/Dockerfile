# embed-service (FastAPI) -- the query-time embedding component. This
# Dockerfile only packages embed_service.py + embedding_model.py; the
# offline scripts (ingest/preprocess/build_index/EDA) are run ad hoc,
# not containerized as a long-running service.
FROM python:3.12-slim
WORKDIR /app

COPY requirements-service.txt .
RUN pip install --no-cache-dir -r requirements-service.txt

COPY src/embedding_model.py src/embed_service.py ./

# Pre-download the model at build time, not at container startup: keeps
# startup fast and means the container doesn't need network access to
# Hugging Face every time it (re)starts.
RUN python -c "from embedding_model import get_model; get_model()"

EXPOSE 8000
CMD ["uvicorn", "embed_service:app", "--host", "0.0.0.0", "--port", "8000"]
