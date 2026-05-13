# MediQuery — Medical AI Chatbot: Project Summary

**Author:** Kinza  
**Version:** 2.1 (Production Ready)  
**Last Updated:** May 13, 2026

---

## What is MediQuery?

MediQuery is an AI-powered medical chatbot that answers health questions using a verified medical knowledge base. It uses a Retrieval-Augmented Generation (RAG) pipeline — retrieving relevant passages from medical documents before generating a structured, evidence-based response.

---

## Architecture Overview

```
User Query
    │
    ▼
Query Rewriter (Llama 3.1 8B)
    │  - Fix typos
    │  - Resolve pronouns (last exchange only)
    │  - Remove filler words
    ▼
Intent Detection → Metadata Filter
    │  - symptoms / causes / treatment / diagnosis / prevention / complications
    ▼
Hybrid Retrieval
    │  - BM25 (40%) + Dense MMR (60%)
    │  - Chunk cleaning (remove timestamps, UI artifacts)
    ▼
Cross-Encoder Reranking (top 8 chunks)
    │
    ▼
LLM Generation (Llama 3.3 70B)
    │  - Query-adaptive structured output
    │  - ## Section headers only for relevant sections
    │  - Disclaimer at end only
    ▼
Post-Processing
    │  - Remove mid-content disclaimers
    │  - Fix "When to Seek" section
    │  - Append safety note if missing
    ▼
Structured Response → User
```

---

## Key Design Decisions

### 1. Query-Adaptive Responses
The system prompt instructs the LLM to only include sections relevant to the question type. "What causes X?" gets `## Causes` only — not all 7 sections.

### 2. Pronoun Resolution (Last Exchange Only)
The query rewriter receives only the last 2 messages (1 exchange) to prevent picking up topics from earlier in the conversation. This fixes the bug where "what are the causes?" after discussing anxiety would return lung cancer causes.

### 3. Chunk Cleaning
Retrieved PDF chunks are cleaned before being sent to the LLM: timestamps, UI artifacts, page numbers, and broken whitespace are removed.

### 4. Offline Model Loading
`TRANSFORMERS_OFFLINE=1` forces HuggingFace to use the local model cache, eliminating startup delays from network retries when `huggingface.co` is unreachable.

### 5. Disclaimer Placement
Post-processing (`restructure_response()`) detects and removes `## When to Seek Medical Attention` sections that only contain generic consult sentences. The disclaimer is always placed as `*italic text*` after `---` at the very end.

### 6. Faithfulness Breakthrough
By implementing a strictly grounded system prompt and using the Llama 3.3 70B model, the system achieved a **Faithfulness score of 88.7%**. This effectively solves the hallucination issue common in earlier RAG versions (which scored 0% in initial tests).

---

## Knowledge Base

- **Source**: Gale Encyclopedia of Medicine (`data/Medical_book.pdf`)
- **Chunks**: ~8,814 indexed in Pinecone
- **Embedding model**: BAAI/bge-small-en-v1.5 (384-dim)
- **Chunking**: Hybrid token-aware (200 tokens prose / 100 tokens structured)

---

## Models Used

| Model | Provider | Purpose |
|-------|----------|---------|
| Llama 3.3 70B Versatile | Groq | Answer generation |
| Llama 3.1 8B Instant | Groq | Query rewriting |
| bge-small-en-v1.5 | HuggingFace (local) | Embeddings |
| ms-marco-MiniLM-L-6-v2 | HuggingFace (local) | Cross-encoder reranking |

---

## Running the Project

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables in .env
PINECONE_API_KEY=...
GROQ_API_KEY=...
FLASK_SECRET_KEY=...
TRANSFORMERS_OFFLINE=1

# Run
set TRANSFORMERS_OFFLINE=1 && python app.py
```

Open `http://127.0.0.1:5000`

---

## Testing

```bash
# Run all tests
python run_tests.py

# Run specific category
python run_tests.py smoke
python run_tests.py regression
python run_tests.py security

# With coverage
python run_tests.py --coverage
```

Test files in `tests/`:
- `test_app.py` — unit tests
- `test_smoke.py` — sanity checks
- `test_regression.py` — regression tests
- `test_functional.py` — end-to-end flows
- `test_integration.py` — pipeline integration
- `test_security.py` — XSS, SQL injection, input validation
- `test_performance.py` — response times, caching, concurrency
