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

- **Hybrid retrieval** combining BM25 keyword search and vector similarity search, fused via Reciprocal Rank Fusion, then re-ranked with a cross-encoder for precision
- **SSE token streaming** — answers stream to the client as the LLM generates them, not as one blocking response
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
│  └── Cross-encoder re-rank (sentence-transformers)        │
└─────────────────────────────────────────────────────────┘
      │
      ├───────────────────┬─────────────────────┬──────────────────────┐
      ▼                   ▼                     ▼                      ▼
┌──────────────┐   ┌─────────────────┐   ┌──────────────────────┐
│  MongoDB     │   │  Vector Store   │   │  LLM Provider        │
│  (metadata)  │   │  ├── FAISS      │   │  ├── Gemini          │
└──────────────┘   │  └── Mongo Atlas│   │  ├── DeepSeek/OpenAI │
                   └─────────────────┘   │  └── Modal (Qwen 3)  │
                                         └──────────────────────┘
```

## Retrieval Pipeline

Retrieval combines three signals rather than relying on vector similarity alone:

1. **Vector search** runs once per LLM-expanded query variant against the configured vector store (MongoDB Atlas Vector Search or FAISS).
2. **BM25** (`rank_bm25`) scores the same document's chunks against the original literal question, catching exact keyword/entity matches that embeddings can miss.
3. **Reciprocal Rank Fusion** (k=60) merges all rankings by rank position, with no score normalization needed between BM25's unbounded scores and vector similarity's bounded ones.
4. **Cross-encoder re-ranking** (`cross-encoder/ms-marco-MiniLM-L-6-v2`, lazily loaded) scores the fused candidate pool directly against the question and selects the final top-k passed to the LLM.

See `app/services/retrieval.py` for the implementation, and [Evaluation](#evaluation) below for the measured impact.

## Streaming

`POST /api/v1/ask/stream` streams the answer via Server-Sent Events instead of returning one blocking JSON response. Retrieval (query expansion → hybrid search → re-rank) runs to completion first, then the response streams:

1. `queries` — the expanded query variants used for retrieval
2. `sources` — the retrieved chunks with their vector/BM25/fused/rerank scores
3. `token` — one event per generated token/delta
4. `done` — final answer text plus latency and token-usage metrics

Consumed via `fetch()` + `ReadableStream` (not `EventSource`, since the endpoint needs the `Authorization` header). The non-streaming `POST /api/v1/ask/` endpoint is kept alongside it for simple request/response use (e.g. the eval harness, Swagger UI).

## Evaluation

`eval/` contains a standalone recall@5 harness comparing three retrieval modes — `vector` (pre-hybrid baseline), `hybrid` (BM25+RRF), and `hybrid_rerank` (the live pipeline) — against ~20 hand-authored Q&A pairs over the bundled Led Zeppelin sample document, run through the exact same `retrieve()` function the API uses.

```bash
python -m eval.run_eval
```

Results are written to `eval/results/report.md` (per-question hit/miss table + summary) and `eval/results/report.json`.

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
| `/api/v1/auth/register` | POST | Register new user |
| `/api/v1/auth/login` | POST | Authenticate and receive JWT |

### Documents
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/documents` | POST | Upload and process document |
| `/api/v1/documents` | GET | List user's documents |

### Question Answering
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ask` | POST | Ask a question, get one JSON response (`{queries, answer, sources}`) |
| `/api/v1/ask/stream` | POST | Ask a question, stream the answer via SSE (`queries` → `sources` → `token`* → `done`) |

### System
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with LLM status |
| `/api/v1/usage` | GET | Current rate limit usage |
| `/api/v1/metrics` | GET | LLM inference metrics (latency, tokens) |
| `/api/v1/metrics/summary` | GET | Aggregated metrics by model/method |

## License

MIT License - Nicolás Japas