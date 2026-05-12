# Medical AI Chatbot: Master Technical Report

**Author:** Kinza  
**Last Updated:** May 2026  
**Version:** 2.0

This document provides a comprehensive breakdown of the Medical AI Chatbot's architecture, logic, and implementation. It reflects the current production codebase.

---

## 1. Executive Summary

MediQuery is a Retrieval-Augmented Generation (RAG) medical chatbot that answers health questions using a verified medical knowledge base. Instead of relying on the LLM's internal knowledge, it retrieves relevant passages from indexed medical documents before generating a grounded, structured response.

**Key features in v2.0:**
- Hybrid BM25 + Dense retrieval with Cross-Encoder reranking
- Intent-based metadata filtering (symptoms / causes / treatment / etc.)
- Query rewriting with pronoun resolution (last-exchange only)
- Query-adaptive structured responses (only relevant sections shown)
- Chunk cleaning before LLM context injection
- Offline-capable (TRANSFORMERS_OFFLINE=1 for local model cache)
- New conversation button, dark mode, responsive UI

---

## 2. Data Ingestion & Chunking

### Source
- **File**: `data/Medical_book.pdf` (Gale Encyclopedia of Medicine)
- **Total chunks indexed**: ~8,814

### Hybrid Token-Aware Chunking Pipeline (`src/helper.py`)

| Stage | Description |
|-------|-------------|
| 1. PDF Loading | PyMuPDF layout-aware extraction (single `fitz.open()` per file) |
| 2. Heading Detection | Font-size + bold flag (primary), regex patterns (secondary) |
| 3. Subsection Boundaries | Medical keywords: causes, symptoms, diagnosis, treatment, etc. |
| 4. Content Classification | `prose` (200 token budget) vs `structured` (100 token budget) |
| 5. Sentence Tokenization | NLTK Punkt tokenizer (handles medical abbreviations) |
| 6. Token-Aware Chunking | tiktoken cl100k_base + 1.10x BGE correction factor |
| 7. Deduplication | MD5 fingerprint-based; boilerplate removal |
| 8. Metadata Enrichment | source, page, section, chunk_index, content_type, token_count |
| 9. Section Prefixing | `[Section Name]\n{chunk_text}` |

---

## 3. Vector Embeddings

- **Model**: `BAAI/bge-small-en-v1.5` (384-dim, retrieval-optimised)
- **Query prefix**: `"Represent this sentence for searching relevant passages: {query}"` (query time only)
- **Normalization**: L2 normalized for cosine similarity
- **Device**: CPU
- **Offline**: Loaded from local HuggingFace cache (`TRANSFORMERS_OFFLINE=1`)

---

## 4. Vector Database (Pinecone)

- **Index**: `medical-chatbot`
- **Chunks**: ~8,814
- **Dimension**: 384
- **Metric**: Cosine similarity

---

## 5. Query Rewriting

**Model**: `llama-3.1-8b-instant` via Groq  
**History passed**: Last 1 exchange only (2 messages) — prevents picking up old topics

**Process:**
1. Greetings/personal questions → passthrough unchanged
2. Typo correction (diabtes → diabetes, symtoms → symptoms)
3. Pronoun resolution using ONLY the last exchange (it/this/that → most recent topic)
4. Filler word removal
5. Output: 3-10 word search query

**Separate history formatters:**
- `format_chat_history()` → last 6 messages (for answer generation)
- `format_rewrite_history()` → last 2 messages, assistant truncated to 200 chars (for rewriting)

---

## 6. Retrieval Pipeline

### Stage 1: Parallel Recall

| Retriever | Weight | Method |
|-----------|--------|--------|
| BM25 | 40% | Keyword exact matching, cached at startup |
| Dense (MMR) | 60% | Semantic search, k=10, fetch_k=20, lambda_mult=0.6 |

### Stage 2: Metadata Filtering (Intent Detection)

| Query Intent | Pinecone Filter Sections |
|---|---|
| symptoms / signs | Symptoms, Signs, Clinical Presentation |
| causes / etiology | Causes, Etiology, Risk Factors, Pathophysiology |
| treatment / medication | Treatment, Management, Therapy, Medications |
| prevention | Prevention, Prophylaxis |
| diagnosis / tests | Diagnosis, Tests, Investigations |
| complications / prognosis | Complications, Prognosis, Outcomes |
| what is / overview | Description, Overview, Definition |

BM25 results are post-filtered in Python using the same section allowlist.

### Stage 3: Cross-Encoder Reranking

- **Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Top-N**: 8 most relevant chunks
- Runs locally on CPU

### Stage 4: Chunk Cleaning (`_clean_chunk()`)

Before sending to the LLM, each chunk is cleaned:
- Remove timestamps (22:44)
- Remove UI artifacts (page numbers, boilerplate)
- Collapse broken newlines and extra whitespace

---

## 7. Response Generation

**Model**: `llama-3.3-70b-versatile` via Groq  
**Temperature**: 0.1

### Query-Adaptive Structured Prompt (`src/prompt.py`)

The system prompt instructs the LLM to match sections to the question type:

| Question Type | Sections Generated |
|---|---|
| "What is X?" | Overview only |
| "What causes X?" | Brief intro + ## Causes |
| "What are symptoms?" | Brief intro + ## Symptoms |
| "How is X treated?" | Brief intro + ## Treatment + ## Lifestyle Management |
| "How to prevent X?" | Brief intro + ## Prevention |
| "Tell me about X" | Overview + all relevant sections from context |

**Disclaimer rule**: One `*italic sentence*` after `---` at the very end. Never mid-response.

**Emergency rule**: Chest pain / stroke / severe bleeding → `⚠️ SEEK IMMEDIATE EMERGENCY CARE. Call 911 now.`

### Post-Processing Pipeline (`app.py`)

1. `clean_answer_text()` — strip meta-commentary prefixes
2. `format_answer_for_readability()` — normalise bullet markers
3. `restructure_response()` — move mid-content disclaimers to end; remove `## When to Seek Medical Attention` if it only contains a generic consult sentence
4. `append_clinical_safety_note()` — append safety note if LLM omitted one

---

## 8. UI Features

### Chat Interface (`templates/chat.html`)

- **Markdown renderer**: Parses `## Heading`, `- bullets`, `---`, `*italic*`, `**bold**` into proper HTML
- **New conversation**: Clears session, restores welcome card, reattaches chip handlers
- **Dark mode**: Persisted in localStorage
- **Suggestion chips**: Pre-filled example queries
- **Typing indicator**: Animated dots while waiting for response
- **Error handling**: Timeout (30s) and server error messages

### Styling (`static/style.css`)

- Section headers (`## Heading`) → `<h4>` in brand blue with underline
- Disclaimer (`*text*`) → small italic muted text
- Divider (`---`) → `<hr>` separator
- Responsive: sidebar collapses on mobile (≤820px)
- Dark/light theme via CSS custom properties

---

## 9. Session Management

- Session ID: UUID per browser session
- History cap: 20 messages (10 exchanges)
- Answer generation uses last 6 messages
- Query rewriting uses last 2 messages only

---

## 10. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve chat UI |
| `/get` | POST | Process message, return structured response |
| `/clear` | POST | Clear session history |
| `/health` | GET | Health check for load balancers |

---

## 11. Running the App

```bash
# With offline model cache (no HuggingFace network calls)
set TRANSFORMERS_OFFLINE=1 && python app.py

# Or on Linux/Mac
TRANSFORMERS_OFFLINE=1 python app.py
```

App runs at `http://127.0.0.1:5000`

---

## 12. Technology Stack

| Component | Technology |
|-----------|------------|
| Framework | Flask |
| Frontend | HTML/CSS/JS (jQuery) |
| Embeddings | BAAI/bge-small-en-v1.5 |
| Vector DB | Pinecone |
| LLM (answers) | Groq — Llama 3.3 70B Versatile |
| LLM (rewrite) | Groq — Llama 3.1 8B Instant |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| PDF Processing | PyMuPDF + NLTK |
| Token Counting | tiktoken (cl100k_base) |
| Evaluation | Ragas |
| Testing | pytest + pytest-cov + pytest-mock |
