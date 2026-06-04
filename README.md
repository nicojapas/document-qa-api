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

A production-ready RAG (Retrieval-Augmented Generation) backend that enables document-grounded question answering. Upload documents, ask natural language questions, and receive accurate answers sourced directly from your content.

## Key Features

- **Multi-provider LLM support** with runtime model switching (Gemini, DeepSeek, self-hosted via Modal)
- **Self-hosted LLM option** using Qwen 3 on Modal's serverless GPU infrastructure
- **Document processing** for PDF, TXT, and DOCX formats
- **Pluggable vector store** with MongoDB Atlas Vector Search (production) and FAISS (local) options
- **JWT authentication** with per-user document isolation
- **Rate limiting** with global daily caps and per-IP throttling
- **Health monitoring** with LLM availability status and warm-up detection
- **LLM observability** with latency tracking, token throughput metrics, and automated alerting

## Architecture

```
Client Request
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  FastAPI                                                │
│  ├── Auth (JWT)                                         │
│  ├── Documents (upload / list / delete)                 │
│  └── QA (question → answer)                             │
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
      ├───────────────────┬─────────────────────┬──────────────────────┐
      ▼                   ▼                     ▼                      ▼
┌──────────────┐   ┌─────────────────┐   ┌──────────────────────┐
│  MongoDB     │   │  Vector Store   │   │  LLM Provider        │
│  (metadata)  │   │  ├── FAISS      │   │  ├── Gemini          │
└──────────────┘   │  └── Mongo Atlas│   │  ├── DeepSeek        │
                   └─────────────────┘   │  └── Modal (Qwen 3)  │
                                         └──────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI, Pydantic V2, async/await |
| Database | MongoDB Atlas |
| Vector Store | MongoDB Atlas Vector Search, FAISS |
| LLM Providers | Google Gemini, DeepSeek, Modal (self-hosted) |
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
| `/api/v1/documents/{id}` | DELETE | Delete document |

### Question Answering
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/qa` | POST | Ask a question about a document |

### System
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with LLM status |
| `/api/v1/usage` | GET | Current rate limit usage |
| `/api/v1/metrics` | GET | LLM inference metrics (latency, tokens) |
| `/api/v1/metrics/summary` | GET | Aggregated metrics by model/method |

## License

MIT License - Nicolás Japas