# Semantic Recommendation Microservice

A natural-language product recommendation service for a fashion e-commerce
catalog. Ask for *"an outfit to go to the beach this summer"* instead of
typing keywords — the service parses intent, runs vector similarity search
over a real product catalog, and (when an LLM key is configured) re-ranks
results with a plain-English rationale for each pick.

## Problem

Traditional keyword search only matches literal words: searching `"t-shirt"`
finds t-shirts, but searching `"something for the beach"` finds nothing,
even when the perfect linen shirt is in stock. This service replaces
keyword matching with **semantic** matching — the query and every product
are embedded into the same vector space, so "beach" surfaces breathable
fabric, swimwear, and sun protection by meaning, not literal text overlap.

## Architecture

Full diagram: **[`docs/Semantic_recommendation_system.pdf`](docs/Semantic_recommendation_system.pdf)**

The system is two halves that only ever talk through one shared artifact
(the pgvector index) and one internal call (embed-service):

```
OFFLINE (Python, run once/on refresh)          ONLINE (always running)
─────────────────────────────────────          ─────────────────────────────
Hugging Face dataset                            Frontend UI (frontend/)
   │                                                │
   ▼                                                ▼
Ingest + EDA + Preprocess                       Spring Boot REST API
   │  (clean fields, build product_text)             │
   ▼                                                ▼
Embed (bge-small-en-v1.5)  ◄──same model──►     Understand Intent
   │                              │              (Spring AI ChatClient, LLM #1)
   ▼                              │                  │
Index ──────► pgvector ◄──────────┘                  ▼
              (PostgreSQL)                       Embed Query → embed-service (FastAPI)
                   ▲                                 │
                   └──────────── Retrieve ◄───────────┘
                                    │
                                    ▼
                              Re-rank (Spring AI ChatClient, LLM #2)
                                    │
                                    ▼
                              Guard & Respond (grounding check + fallback)
                                    │
                                    ▼
                              Response → rendered in Frontend UI
```

**Why it's split this way, in one sentence each:**

- **Python owns the model** (training/embedding) — `sentence-transformers`
  and the Hugging Face ecosystem live there, not in Java.
- **Spring AI is the only place a model gets *called*** at request time —
  both LLM calls (intent parsing, re-ranking) go through Spring AI's
  `ChatClient`, making the LLM provider a config change, not a rewrite.
- **`embed-service` (FastAPI)** runs the *exact same* embedding model used
  to build the index, so query vectors and catalog vectors are always
  comparable — Java never embeds text itself.
- **Every result is checked before it ships.** `ResponseGuardService`
  verifies each returned product actually exists in the candidate set the
  LLM saw, and falls back to pure vector-similarity ranking (not an error)
  if the LLM is unavailable or its output can't be grounded.

## Configuration — LLM API key

The service works correctly with **zero configuration** — no key set means
vector-similarity results only (`degraded: true`), not an error. A key
unlocks LLM-powered query understanding and re-ranked results with a
written rationale. This is optional but worth setting up correctly, since
every step below reflects an actual mistake made (and fixed) while building
this:

1. **Create a key** at [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
2. **Enable billing on that account** at [platform.openai.com/settings/organization/billing](https://platform.openai.com/settings/organization/billing)
   — a brand-new key with no billing method returns `HTTP 429
   insufficient_quota` on every call. This looks like a config bug; it
   isn't one. If you see this error, it's billing, not the code.
3. **Set it in your shell**, not in any file in this repo:
   ```bash
   export OPENAI_API_KEY=sk-...
   ```
   For it to persist across terminal sessions, add that line to your shell
   profile (`~/.zshrc` on macOS by default). **A shell that's already
   running won't pick up a profile edit retroactively** — profiles are read
   once, at shell startup — so either open a new terminal or run `source
   ~/.zshrc` in the one you're using.
4. **Never put the key in `application.yml`, `docker-compose.yml`, or any
   committed file.** `application.yml` reads it from the environment
   (`${OPENAI_API_KEY:sk-not-configured}`) specifically so it never needs to
   be hardcoded. In `docker-compose.yml`, `recommendation-service`'s
   `environment:` list has a bare `OPENAI_API_KEY` entry (no `=value`) — that
   syntax passes the variable through from whatever shell you run `docker
   compose` / `./setup.sh` in, *if* it's set there, and otherwise leaves it
   genuinely unset in the container (not an empty string) so the safe
   placeholder in `application.yml` still applies. Run `setup.sh` from the
   same shell where you exported the key.
5. **Confirm it worked**: a request to `/api/v1/recommendations` should
   return `"degraded": false` with a populated `parsedIntent` and an
   LLM-written `rationale` per result (see [Sample usage](#sample-usage)).

## Quick start

```bash
git clone <this-repo>
cd semantic-recommendation-system
export OPENAI_API_KEY=sk-...   # optional -- see Configuration above
./setup.sh
```

`setup.sh` is idempotent — safe to re-run. It will:

1. Check prerequisites (Docker, Docker Compose, Python 3.10+, JDK 21+)
2. Start Postgres/pgvector
3. Build the Python virtualenv, stream ~300 real Amazon Fashion products
   from Hugging Face, clean them, embed them, and index them
4. Build and start `embed-service`, `recommendation-service`, and `frontend`
5. Health-check every service
6. Run the retrieval-quality evaluation and print real metrics

### Manual setup (if you'd rather run each step yourself)

```bash
# 1. Postgres
docker compose up -d --wait postgres

# 2. Data pipeline
cd data-pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd src
python ingest.py       # streams ~300 real products from Hugging Face
python preprocess.py   # cleans fields, builds product_text
python build_index.py  # embeds with bge-small-en-v1.5, loads pgvector
cd ../..

# 3. Application services
docker compose up -d --build --wait embed-service recommendation-service frontend
```

## Health check

Once everything is up:

```bash
docker compose ps                              # all 4 containers should show "Up" / "healthy"
curl http://localhost:8001/health               # embed-service -> {"status":"ok","dim":384}
curl -X POST http://localhost:8080/api/v1/recommendations \
  -H "Content-Type: application/json" -d '{"query":"health check"}'   # -> HTTP 200
curl -o /dev/null -w "%{http_code}\n" http://localhost:5500/           # frontend -> 200
```

`setup.sh` runs all of this automatically as its step 5 and fails loudly
(non-zero exit, clear message pointing at `docker compose logs <service>`)
if anything doesn't come up healthy.

## Sample usage

```bash
curl -s -X POST http://localhost:8080/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"query": "I need an outfit to go to the beach this summer", "topK": 5}'
```

```json
{
  "parsedIntent": {
    "rewrittenQuery": "I need an outfit to go to the beach this summer",
    "category": null, "occasion": null, "season": null,
    "priceMin": null, "priceMax": null
  },
  "results": [
    { "parentAsin": "B07DJ2XG61", "title": "Queensun Mesh Beach Bag with Insulated Picnic Cooler...", "averageRating": 3.7, "rationale": "Matched on similarity to your query.", "score": 0.685 }
  ],
  "degraded": true,
  "degradedReason": "LLM re-rank unavailable or returned no grounded results; showing vector-similarity ranking."
}
```

`degraded: true` means no (or no working) `OPENAI_API_KEY` was set — the
results above are still real, live vector search, just without the LLM's
rewritten intent and rationale. With a working key, the same call returns
`degraded: false`, populated `parsedIntent` fields, and an LLM-written
rationale per result.

Or use the browser UI at **http://localhost:5500** once `setup.sh` finishes.

## Evaluating the RAG solution — real metrics, not a smoke test

`data-pipeline/tests/` has an actual evaluation harness, not just spot
checks:

```bash
cd data-pipeline/src && source ../.venv/bin/activate
cd ../tests
python evaluate_retrieval.py          # human-readable Precision@K report
python -m pytest test_retrieval_quality.py -v   # pass/fail regression gate
```

**Methodology:** no official relevance judgments exist for this dataset, so
`golden_queries.py` defines 15 natural-language queries with hand-written
relevance rules (keywords), calibrated against an actual keyword census of
the indexed 300-product sample. For each query, Precision@K is computed for
(a) the real vector-search path this service uses and (b) a naive
keyword-matching baseline standing in for classic keyword search — the
thing this project exists to improve on.

**Measured result** (`setup.sh`-verified run, K=5, 300-product sample —
expect small run-to-run variance since `ingest.py` streams live from
Hugging Face on every run; conclusions below are stable across runs):

| | Vector search | Keyword baseline |
|---|---|---|
| Avg. Precision@5 | **0.87** | 0.80 |
| Avg. Precision@10 | 0.74 | 0.78 |

**Read honestly, not as a win:** the relevance proxy is keyword presence,
which structurally *favors* the keyword baseline — it's judged by exactly
the signal it optimizes for. Vector search still winning at K=5 despite
that bias is the real signal (it's catching paraphrases/semantic matches
keyword search misses); the K=10 near-tie is not a regression, it's the
baseline exhausting more exact-text matches as K grows. One query —
*"hiking gear for cold weather"* — scores nowhere near either method's
average (0.0 vector / 0.20 keyword): only 6 of 300 sampled products mention
hiking at all, a catalog-coverage limit of this 300-item sample, not a
retrieval bug (`golden_queries.py` documents the full keyword census behind
every query).

## Known limitations

- **Sample size**: `data-pipeline/src/ingest.py` caps the pull at 300
  products (`SAMPLE_SIZE`) to keep setup fast, out of a ~800k-row category.
  Remove the cap to index the full catalog.
- **Price data**: most listings in this raw metadata slice have a `null`
  price — this is a property of the source data, not a bug. Price-filtered
  queries will legitimately return fewer results until a fuller pull is
  indexed.
- **Embedding model is pretrained, not fine-tuned** on this catalog yet —
  a deliberate next step, not an oversight. Fine-tuning needs
  LLM-synthesized training pairs and GPU time outside this project's scope.
- **A cross-encoder re-rank stage** (narrowing candidates further before the
  LLM re-rank call) and a **Testcontainers/WireMock Java test suite** are
  both scoped, sensible fast-follows, not yet built.

## Repo layout

```
semantic-recommendation-system/
├── README.md                   <- you are here
├── setup.sh                    <- one-shot reviewer setup
├── docker-compose.yml
├── docs/                       <- architecture diagram (PDF)
├── data-pipeline/               (Python)
│   ├── src/                    <- ingest -> preprocess -> build_index; embed_service.py
│   ├── tests/                  <- retrieval-quality evaluation harness
│   ├── notebooks/eda.ipynb     <- exploratory data analysis
│   └── Dockerfile              <- embed-service image
├── recommendation-service/      (Java -- Spring Boot + Spring AI, all model calling)
│   ├── src/main/java/com/example/reco/
│   └── Dockerfile
└── frontend/                    (single-file HTML/JS search UI)
    └── Dockerfile
```

## Tech stack

| Layer | Technology |
|---|---|
| Data source | Amazon Reviews 2023 (Fashion metadata), streamed from Hugging Face |
| Embedding model | `bge-small-en-v1.5` (sentence-transformers), self-hosted |
| Vector store | PostgreSQL + pgvector |
| Query-time embedding | FastAPI (`embed-service`) |
| Application / orchestration | Spring Boot + Spring AI (Java 21) |
| LLM | OpenAI, via Spring AI `ChatClient` (provider-swappable) |
| Frontend | Single-file HTML/JS, no build step |
| Deployment | Docker Compose, 4 services on one network |
