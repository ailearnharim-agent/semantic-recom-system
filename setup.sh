#!/usr/bin/env bash
# Semantic Recommendation Microservice -- one-shot reviewer setup.
#
# Brings up Postgres, builds the product index (real data, streamed live
# from Hugging Face), builds and starts the embed-service / recommendation-
# service / frontend containers, health-checks everything, then runs the
# retrieval-quality evaluation and prints real metrics.
#
# Safe to re-run: every step is idempotent (upserts, not inserts; `docker
# compose up` reuses what's already there).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

info()  { printf "\n\033[1;34m==>\033[0m %s\n" "$1"; }
ok()    { printf "\033[1;32m  ok\033[0m  %s\n" "$1"; }
fail()  { printf "\033[1;31m  FAIL\033[0m %s\n" "$1"; exit 1; }

# ---------------------------------------------------------------------------
info "1/6 Checking prerequisites"
command -v docker >/dev/null 2>&1 || fail "docker not found -- install Docker Desktop: https://www.docker.com/products/docker-desktop"
docker info >/dev/null 2>&1 || fail "Docker daemon not running -- start Docker Desktop and re-run this script"
docker compose version >/dev/null 2>&1 || fail "docker compose plugin not found (should ship with Docker Desktop)"
command -v python3 >/dev/null 2>&1 || fail "python3 not found -- install Python 3.10+"
command -v java >/dev/null 2>&1 || fail "java not found -- install JDK 21+"
command -v curl >/dev/null 2>&1 || fail "curl not found"
ok "docker, docker compose, python3, java, curl all present"

# ---------------------------------------------------------------------------
info "2/6 Starting Postgres (pgvector)"
docker compose up -d --wait postgres
ok "postgres healthy"

# ---------------------------------------------------------------------------
info "3/6 Building the product index (Python data pipeline)"
cd "$ROOT_DIR/data-pipeline"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
ok "python dependencies installed"

cd src
python ingest.py
python preprocess.py
python build_index.py
cd "$ROOT_DIR"
ok "catalog ingested, cleaned, embedded, and indexed into pgvector"

# ---------------------------------------------------------------------------
info "4/6 Building and starting embed-service, recommendation-service, frontend"
docker compose up -d --build --wait embed-service recommendation-service frontend
ok "all containers started"

# ---------------------------------------------------------------------------
info "5/6 Health check"
docker compose ps

EMBED_HEALTH=$(curl -sf http://localhost:8001/health || echo "UNREACHABLE")
echo "embed-service  (:8001/health)        -> $EMBED_HEALTH"

# recommendation-service has no built-in healthcheck (no actuator dependency
# yet -- documented fast-follow), and this check can run just after the
# container was (re)created, so it needs a poll loop, not a single shot --
# and every curl here is defended against `set -e` killing the script
# silently on a connection-refused before our own error message can print.
RECO_STATUS="000"
for _ in $(seq 1 30); do
  RECO_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8080/api/v1/recommendations \
    -H "Content-Type: application/json" -d '{"query":"health check"}' || echo "000")
  [ "$RECO_STATUS" = "200" ] && break
  sleep 2
done
if [ "$RECO_STATUS" = "200" ]; then
  echo "recommendation-service (:8080)       -> HTTP 200"
else
  fail "recommendation-service returned HTTP $RECO_STATUS after 60s -- check: docker compose logs recommendation-service"
fi

FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5500/ || echo "000")
if [ "$FRONTEND_STATUS" = "200" ]; then
  echo "frontend       (:5500)               -> HTTP 200"
else
  fail "frontend returned HTTP $FRONTEND_STATUS -- check: docker compose logs frontend"
fi
ok "all services healthy and responding"

# ---------------------------------------------------------------------------
info "6/6 Evaluating retrieval quality (real metrics, not a smoke test)"
cd "$ROOT_DIR/data-pipeline/tests"
python evaluate_retrieval.py
echo
python -m pytest test_retrieval_quality.py -v
cd "$ROOT_DIR"

# ---------------------------------------------------------------------------
cat <<EOF

============================================================
Setup complete.

  Frontend:              http://localhost:5500
  Recommendation API:    http://localhost:8080/api/v1/recommendations
  Embed-service health:  http://localhost:8001/health
  Postgres:               localhost:5434 (user/pass: reco/reco)

  LLM-powered mode requires OPENAI_API_KEY to be set in your shell before
  this script runs. Without it, the service still works -- it falls back
  to vector-similarity ranking (see docs/DECISIONS.md, ADR-15/ADR-23).
============================================================
EOF
