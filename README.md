# Document QA API

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.112.0-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?logo=mongodb&logoColor=white)](https://www.mongodb.com/atlas)
[![LangChain](https://img.shields.io/badge/LangChain-0.3-1C3C3C?logo=langchain&logoColor=white)](https://langchain.com)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-AI-4285F4?logo=google&logoColor=white)](https://ai.google.dev)
[![DeepSeek](https://img.shields.io/badge/DeepSeek-V4_Flash-5C6BC0)](https://deepseek.com)
[![FAISS](https://img.shields.io/badge/FAISS-Vector_Search-blue)](https://github.com/facebookresearch/faiss)
[![Modal](https://img.shields.io/badge/Modal-Serverless_GPU-6366F1)](https://modal.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-ready RAG (Retrieval-Augmented Generation) backend that enables document-grounded question answering. Upload documents, ask natural language questions, and receive accurate answers sourced directly from your content, streamed token-by-token to a Next.js frontend.

## Key Features

- **Hybrid retrieval** combining BM25 keyword search and vector similarity search, fused via Reciprocal Rank Fusion, then re-ranked via the hosted Voyage AI rerank API for precision
- **SSE streaming throughout** — both ingestion and question-answering report live, step-by-step progress (not just the final answer token-by-token) instead of one blocking response
- **Multi-provider LLM support** with runtime model switching (Gemini, DeepSeek, OpenAI, self-hosted via Modal)
- **Self-hosted LLM option** using Qwen 3 on Modal's serverless GPU infrastructure
- **Document processing** for PDF, TXT, and DOCX formats
- **Pluggable vector store** with MongoDB Atlas Vector Search (production) and FAISS (local) options
- **Retrieval evaluation harness** measuring recall@5 to quantify the hybrid+rerank improvement over vector-only search
- **JWT authentication** with per-user document isolation
- **Rate limiting** with global daily caps and per-IP throttling
- **Health monitoring** with LLM availability status and warm-up detection
- **LLM observability** with latency tracking, token throughput metrics, and automated alerting

## Frontend

The companion Next.js App Router frontend lives in [`document-qa-fe`](https://github.com/nicojapas/document-qa-fe) — it drives the SSE `/api/v1/ask/stream` endpoint for live token rendering.

## Architecture

```
Client Request
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  FastAPI                                                │
│  ├── Auth (JWT)                                         │
│  ├── Documents (upload / list)                          │
│  └── QA (question → answer, JSON or SSE stream)         │
└─────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  Processing Pipeline                                    │
│  ├── Text extraction (pdf/txt/docx)                     │
│  ├── Chunking                                           │
│  └── Embedding generation                               │
└─────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  Hybrid Retrieval (app/services/retrieval.py)            │
│  ├── Vector search (per expanded query)                  │
│  ├── BM25 keyword search (rank_bm25)                     │
│  ├── Reciprocal Rank Fusion                               │
│  └── Rerank (Voyage AI, hosted API)                       │
└─────────────────────────────────────────────────────────┘
      │
      ├────────────────────────┬────────────────────┬─────────────────────┐
      ▼                        ▼                    ▼                     ▼
┌────────────────┐   ┌──────────────────┐   ┌──────────────┐   ┌─────────────────────┐
│ MongoDB        │   │ Vector Store     │   │ Reranker     │   │ LLM Provider        │
│ (metadata)     │   │ ├── FAISS        │   │ (Voyage AI,  │   │ ├── Gemini          │
└────────────────┘   │ └── Mongo Atlas  │   │  rerank-2.5) │   │ ├── DeepSeek/OpenAI │
                     └──────────────────┘   └──────────────┘   │ └── Modal (Qwen 3)  │
                                                               └─────────────────────┘
```

## Retrieval Pipeline

Retrieval combines three signals rather than relying on vector similarity alone:

1. **Vector search** runs once per LLM-expanded query variant against the configured vector store (MongoDB Atlas Vector Search or FAISS).
2. **BM25** (`rank_bm25`) scores the same document's chunks against the original literal question, catching exact keyword/entity matches that embeddings can miss.
3. **Reciprocal Rank Fusion** (k=60) merges all rankings by rank position, with no score normalization needed between BM25's unbounded scores and vector similarity's bounded ones.
4. **Re-ranking** via the hosted [Voyage AI](https://www.voyageai.com) rerank API (`rerank-2.5`) scores the fused candidate pool directly against the question and selects the final top-k passed to the LLM. Runs as an HTTP call rather than a locally-loaded cross-encoder, to keep the Render instance's memory footprint down.

See `app/services/retrieval.py` for the implementation, and [Evaluation](#evaluation) below for the measured impact.

## Streaming

Both question-answering and document ingestion have a streaming variant that reports live, step-by-step progress via Server-Sent Events instead of returning (or requiring the client to wait for) one blocking response. Both are consumed via `fetch()` + `ReadableStream` rather than `EventSource`, since they need the `Authorization` header and, for ingestion, a `multipart/form-data` body — neither of which `EventSource` supports.

**`POST /api/v1/ask/stream`** — query expansion and retrieval run first, then the response streams:

1. `queries` — the expanded query variants used for retrieval
2. `retrieval_stage` — one event per retrieval sub-step as it actually completes: `vector` (per-query vector search), `bm25` (keyword search), `fuse` (Reciprocal Rank Fusion), `rerank` (Voyage AI). Retrieval runs as a background task so these arrive incrementally rather than all landing at once after the whole thing finishes.
3. `sources` — the retrieved chunks with their vector/BM25/fused/rerank scores
4. `token` — one event per generated token/delta
5. `done` — final answer text plus latency and token-usage metrics

The non-streaming `POST /api/v1/ask/` endpoint is kept alongside it for simple request/response use (e.g. the eval harness, Swagger UI).

**`POST /api/v1/documents/stream`** — same idea for ingestion:

1. `received` — document metadata saved
2. `split` — text extracted and chunked, with the resulting chunk count
3. `embed` — chunks embedded, with the embedding model used
4. `store` — chunks and vectors written to the configured vector store, with which backend handled it
5. `done` — the created document

Both streams open with a padding comment frame before the first real event — some proxies/CDNs buffer a response until a minimum byte threshold is reached, which would otherwise hold back these (individually tiny) events until the connection closes. The non-streaming `POST /api/v1/documents/` endpoint remains for simple request/response use.

## Evaluation

`eval/` contains a standalone recall@5 harness comparing three retrieval modes — `vector` (pre-hybrid baseline), `hybrid` (BM25+RRF), and `hybrid_rerank` (the live pipeline) — against ~20 hand-authored Q&A pairs over the bundled Led Zeppelin sample document, run through the exact same `retrieve()` function the API uses.

```bash
python -m eval.run_eval
```

Results are written to `eval/results/report.md` (per-question hit/miss table + summary) and `eval/results/report.json`.

A second harness scores generation quality — faithfulness, answer relevancy, and context precision — on the same fixture, running the live retrieve-then-answer pipeline and judging it with [Ragas](https://docs.ragas.io), using the app's existing Gemini LLM and embeddings (no OpenAI key, no local judge model):

```bash
pip install -r requirements.txt -r eval/requirements.txt
python -m eval.run_ragas_eval
```

Results are written to `eval/results/ragas_report.json`. Ragas' deps (`pandas`/`pyarrow`/`datasets`) are kept out of the deployed app's `requirements.txt` on purpose — they'd bloat the Render service for no runtime benefit.

## Tech Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI, Pydantic V2, async/await |
| Frontend | Next.js (App Router), TypeScript, Tailwind |
| Database | MongoDB Atlas |
| Vector Store | MongoDB Atlas Vector Search, FAISS |
| Keyword Search | BM25 (`rank_bm25`) |
| Re-ranking | Cross-encoder (Voyage AI `rerank-2.5`, hosted) |
| Fusion | Reciprocal Rank Fusion |
| Evaluation | Recall@5 harness, Ragas (faithfulness, answer relevancy, context precision) |
| LLM Providers | Google Gemini, DeepSeek, OpenAI, Modal (self-hosted) |
| Self-hosted LLM | vLLM + Qwen/Qwen3-1.7B on Modal |
| Auth | JWT (python-jose) |
| Testing | Pytest |

## LLM Configuration

The API supports three LLM providers with runtime model selection:

| Model | Provider | Notes |
|-------|----------|-------|
| `gemini-2.5-flash` | Google | Fast, cost-effective |
| `deepseek-v4-flash` | DeepSeek | High quality, competitive pricing |
| `qwen3-1.7b` | Modal (self-hosted) | Full control, no external API dependency |

Switch models per request by specifying the `model` parameter, or set a default via `LLM_PROVIDER` environment variable.

The Modal integration uses vLLM serving Qwen3-1.7B on serverless GPU infrastructure. The `/health` endpoint reports LLM availability with warm-up detection for cold starts.

## Observability

The API includes built-in observability for LLM inference:

| Metric | Description |
|--------|-------------|
| **Latency** | Response time (ms) for each LLM call |
| **Token throughput** | Prompt, completion, and total tokens per request |
| **Automated alerts** | Webhook/log alerts when latency exceeds threshold |

Metrics are stored in MongoDB and queryable via the `/api/v1/metrics` endpoints.

Configure via environment variables:
```bash
LLM_LATENCY_THRESHOLD_MS=5000  # Alert threshold (default: 5000ms)
ALERT_WEBHOOK_URL=             # Optional webhook for latency alerts
```

## API Reference

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/login` | POST | Authenticate with the demo user's email/password, receive a JWT |

### Documents
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/documents` | POST | Upload and process document, get one JSON response |
| `/api/v1/documents/stream` | POST | Upload a document, stream ingestion progress via SSE (`received` → `split` → `embed` → `store` → `done`) |
| `/api/v1/documents` | GET | List user's documents |

### Question Answering
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ask` | POST | Ask a question, get one JSON response (`{queries, answer, sources}`) |
| `/api/v1/ask/stream` | POST | Ask a question, stream progress and the answer via SSE (`queries` → `retrieval_stage`\* → `sources` → `token`\* → `done`) |

### System
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with LLM status |
| `/api/v1/usage` | GET | Current rate limit usage |
| `/api/v1/metrics` | GET | LLM inference metrics (latency, tokens) |
| `/api/v1/metrics/summary` | GET | Aggregated metrics by model/method |

## License

MIT License - Nicolás Japas