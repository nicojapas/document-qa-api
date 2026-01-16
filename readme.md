document-qa-api/
├── app/
│   ├── main.py              # App entry point, middleware, & router inclusion
│   ├── api/
│   │   ├── deps.py          # Dependencies (get_db, get_current_user, etc.)
│   │   └── v1/
│   │       ├── api.py       # Global v1 router (includes all sub-routers)
│   │       ├── auth.py      # Login, registration, token endpoints
│   │       ├── documents.py # File upload, list, delete endpoints
│   │       └── qa.py        # Question-answering & chat history endpoints
│   ├── core/
│   │   ├── config.py        # Pydantic Settings (env vars, secrets)
│   │   ├── security.py      # JWT token logic & password hashing
│   │   └── logging.py       # Custom logging for AI tokens/latency
│   ├── db/
│   │   ├── session.py       # MongoDB client (Motor) initialization
│   │   └── indexes.py       # Script to setup Vector Search & TTL indexes
│   ├── models/              # MongoDB (Motor/Beanie) Domain Models
│   │   ├── user.py
│   │   └── document.py
│   ├── schemas/             # Pydantic Data Models (Input/Output validation)
│   │   ├── auth.py          # Token & UserCreate schemas
│   │   ├── document.py      # DocumentResponse & Metadata schemas
│   │   └── qa.py            # QuestionRequest & AnswerResponse schemas
│   ├── services/            # Business Logic & AI Orchestration
│   │   ├── auth.py          # User management logic
│   │   ├── documents.py     # Logic for saving file metadata to DB
│   │   ├── embeddings.py    # OpenAI/HuggingFace embedding logic
│   │   ├── vector_store.py  # MongoDB Atlas Vector Search queries
│   │   └── llm.py           # RAG logic (Prompt engineering + LLM call)
│   └── utils/
│       ├── file_parser.py   # Extracting text from PDF/TXT/DOCX
│       └── text_splitter.py # Chunking logic (RecursiveCharacterSplitter)
│
├── tests/                   # Pytest suite
│   ├── conftest.py          # Test database setup
│   ├── test_api/            # Route tests
│   └── test_services/       # Logic & AI pipeline tests
│
├── .env.example             # Template for API keys (never commit .env)
├── .gitignore
├── Dockerfile               # For future-proofing deployment
├── requirements.txt         # Cleaned list of dependencies
├── README.md                # Documentation & Architecture Diagram
└── pyproject.toml           # Build system configuration
