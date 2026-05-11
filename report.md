# Medical AI Chatbot: Master Technical Report (Beginner to Advanced)

This document provides a comprehensive breakdown of the Medical AI Chatbot's architecture, logic, and evaluation framework. It is designed to be accessible to beginners while providing the technical depth required by advanced developers.

---

## 1. Executive Summary: The RAG Paradigm

Retrieval-Augmented Generation (RAG) is the bridge between a Large Language Model's (LLM) reasoning capabilities and a private, authoritative dataset. Instead of relying on the LLM's internal (and potentially stale) knowledge, RAG forces the AI to look up facts in a curated database before answering.

This implementation features:
- **Hybrid Retrieval**: BM25 (keyword-based) + Dense (semantic) + Cross-Encoder Reranking
- **Metadata Filtering**: Intent-based section filtering for precision
- **Query Rewriting**: LLM-powered contextual query optimization
- **Real-time Backend Logs**: Complete visibility into the RAG pipeline
- **Production Optimizations**: Caching, session management, error handling

---

## 2. Step 1: Data Ingestion & Chunking (The Foundation)

### Beginner: Breaking it Down
We take large PDFs (Medical Books) and cut them into smaller pieces called **Chunks**. 
- **Chunk Size:** We use ~200 tokens for prose, ~100 tokens for structured content
- **Chunk Overlap:** We carry the last 2 sentences into the next chunk for context preservation

### Advanced: Hybrid Token-Aware Chunking Pipeline

The chunking pipeline (`src/helper.py`) implements a sophisticated 9-stage process:

#### Stage 1: PDF Loading with PyMuPDF (Single Parse)
- PDFs are opened ONCE using PyMuPDF's layout-aware extraction
- Each text block captures: font size, bold flag, page number
- Falls back to PyPDFLoader if PyMuPDF fails

#### Stage 2: Layout-Aware Heading Detection
- **Primary**: Font size >15% larger than median → heading
- **Secondary**: Strong regex patterns for medical headings:
  - Numbered sections: `"1.", "1.2", "A.", "I."`
  - ALL-CAPS lines (2-8 words)
  - Title-Case (max 5 words, no verb suffixes like -ing, -tion)
  - Single capitalized medical word (≥4 chars)

#### Stage 3: Subsection Boundary Detection
- Medical keywords trigger new sections: causes, symptoms, diagnosis, treatment, prevention, complications, etc.

#### Stage 4: Content Classification
- Classifies content as 'prose' or 'structured' (bullets/tables/lists)
- Structured content gets smaller token budgets (100 tokens vs 200)

#### Stage 5: NLTK Sentence Tokenization
- Uses Punkt tokenizer for robust sentence segmentation
- Handles medical abbreviations (Dr., mg., etc.) better than regex

#### Stage 6: Token-Aware Semantic Chunking
- **NOT character-based**: Uses tiktoken cl100k_base with BGE correction factor (1.10x)
- Enforces both token budget AND max sentences per chunk (12)
- Sentence-level overlap: carries last 2 sentences to next chunk

#### Stage 7: Deduplication
- MD5 fingerprint-based removal of exact duplicates
- Boilerplate removal (page numbers, copyright, URLs)

#### Stage 8: Metadata Enrichment
Every chunk includes:
- `source`: PDF file path
- `page`: Page number
- `section`: Heading name (e.g., "Symptoms", "Treatment")
- `chunk_index`: Position within section
- `content_type`: "prose" or "structured"
- `token_count`: Estimated BGE token count

#### Stage 9: Section Prefixing
- Each chunk prefixed with `[Section Name]` for retrieval context

---

## 3. Step 2: Vector Embeddings (Mathematical Meaning)

### Beginner: Translating to Numbers
Computers don't understand words; they understand numbers. An **Embedding Model** (we use HuggingFace) turns text into a long list of numbers called a **Vector**. 
- Words with similar meanings (e.g., "Physician" and "Doctor") end up with vectors that are "close" to each other in mathematical space.

### Advanced: BGE-Small-en-v1.5 Implementation

```python
# src/helper.py
class BGEEmbeddingsWrapper(HuggingFaceEmbeddings):
    def embed_query(self, text: str) -> list:
        prefixed = f"Represent this sentence for searching relevant passages: {text}"
        return super().embed_query(prefixed)
```

- **Model**: `BAAI/bge-small-en-v1.5`
- **Dimensions**: 384 (compact, fast)
- **Normalization**: L2 normalized for cosine similarity
- **Query Prefix**: Added at query time only (not indexing) per BGE specification
- **Device**: CPU (no GPU required)

---

## 4. Step 3: Vector Database (Pinecone)

### Beginner: The AI's Library
**Pinecone** is a specialized database that stores these vectors. Traditional databases look for exact words; Pinecone looks for **intent** and **meaning**.

### Advanced: Index Configuration

```python
PineconeVectorStore.from_existing_index(
    index_name="medical-chatbot",
    embedding=get_embeddings(),
)
```

- **Index Name**: `medical-chatbot`
- **Total Chunks**: ~8,845 indexed
- **Dimension**: 384
- **Metric**: Cosine similarity
- **Index Type**: HNSW (Hierarchical Navigable Small World)

---

## 5. Step 4: The Query Rewriter (The Optimizer)

### Beginner: Fixing your Input
Users often use messy language (e.g., "what to eat for it?"). Our **Rewriter** (powered by Groq/Llama) looks at your chat history to figure out what "it" means and fixes your typos.

### Advanced: Contextual Reference Resolution

The rewriter uses few-shot prompting to transform conversational queries:

```python
query_rewrite_system_prompt = """
You are a medical query optimizer. Given a chat history and user query,
rewrite the query to be a standalone search query optimized for medical 
document retrieval.

Examples:
- "What are the symptoms?" + "How is it treated?" → "How is [condition] treated?"
- "Tell me about diabetes" → "Diabetes symptoms causes treatment"
"""
```

**Process Flow:**
1. Check for greetings/personal questions (passthrough, no rewrite)
2. Extract entities from chat history (last 3 exchanges = 6 messages)
3. Resolve pronouns (it → condition from context)
4. Remove filler words
5. Extract clean, keyword-rich query

**Model**: `llama-3.1-8b-instant` (fast, lightweight via Groq)

---

## 6. Step 5: Dual-Stage Retrieval (Retriever + Reranker)

### Beginner: Search vs. Edit
1.  **Retriever**: Finds 15 "likely" answers from the database.
2.  **Reranker**: A second, more precise AI (Cross-Encoder) reads all 15 and picks only the **Top 8** that truly matter.

### Advanced: Hybrid Retrieval Architecture

#### Stage 1: Parallel Recall (BM25 + Dense)
- **BM25 Retriever** (40% weight):
  - Keyword-based exact matching
  - Cached at startup (not rebuilt per request)
  - Post-filtered by section metadata
  
- **Dense Retriever** (60% weight):
  - MMR (Maximum Marginal Relevance) search
  - k=10, fetch_k=20, lambda_mult=0.6
  - Diversity-aware to avoid redundant results

#### Stage 2: Metadata Filtering (Intent Detection)
Six intent categories detected via regex:

| Intent Pattern | Sections Filtered |
|---------------|-------------------|
| symptoms | Symptoms, Signs, Clinical Presentation |
| causes | Causes, Etiology, Risk Factors |
| treatment | Treatment, Management, Therapy, Medications |
| prevention | Prevention, Prophylaxis |
| diagnosis | Diagnosis, Tests, Investigations |
| complications | Complications, Prognosis |

#### Stage 3: Cross-Encoder Reranking
- **Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Top-N**: 8 most relevant chunks
- Runs locally on CPU

#### Stage 4: Optional LLM Extraction
- **Flag**: `ENABLE_EXTRACTOR=1` (disabled by default for speed)
- Uses `llama-3.1-8b-instant` to extract only relevant sentences from each chunk

---

## 7. Step 6: Generation (The Expert Consultant)

### Beginner: Writing the Answer
The AI (Groq/Llama 3.3) takes the Top 8 chunks and writes a professional response. We use a **System Prompt** to tell it to be empathetic, professional, and to NEVER lie.

### Advanced: Production-Ready RAG Chain

```python
# Chain composition
chain = (
    RunnablePassthrough.assign(
        context=RunnableLambda(_retrieve_with_filter)  # Per-request retrieval
    )
    | RunnableLambda(_build_prompt)                    # Dynamic prompt
    | llm                                               # Groq LLM
    | StrOutputParser()                                 # String output
)
```

#### System Prompt Features:
- **Role**: Medical information assistant
- **Constraints**: 
  - Only use provided context
  - Include disclaimer about professional medical advice
  - Be empathetic and clear
  - Use bullet points for list questions

#### Answer Post-Processing:
1. **Clean**: Remove boilerplate prefixes ("Based on the provided context...")
2. **Format**: Convert to readable bullet lists for cause/symptom questions
3. **Safety Note**: Append clinical disclaimer for medication/treatment queries

#### Session Memory:
- Capped at 20 messages (10 exchanges)
- Last 3 exchanges used for pronoun resolution
- Stored in Flask session

---

## 8. Step 7: UI Features

### New Conversation Button
The sidebar includes a "New conversation" button that:
- Confirms before clearing
- Calls `/clear` endpoint to reset session
- Restores welcome card with suggestion chips
- Clears logs panel

### Backend Logs Panel
A toggleable panel (clipboard icon in topbar) displays:
- Original user query
- Rewritten query (after LLM processing)
- Metadata filters applied
- Number of documents retrieved
- Document previews with section names
- Response generation status

Each log entry shows: timestamp, level (INFO/WARNING/ERROR), message

---

## 9. Step 8: Evaluation (The Metrics)

We use the **Ragas** framework (powered by Groq) to scientifically measure our quality:

| Metric | Description | Target |
|--------|-------------|--------|
| Faithfulness | Does the answer come *only* from the context? | > 0.8 |
| Answer Relevance | Does it actually answer the user? | > 0.85 |
| Context Precision | Did the Reranker do its job correctly? | > 0.75 |
| Context Recall | Do we have enough info in our database? | > 0.7 |

---

## 10. Production Optimizations

### Caching Strategy
All heavy objects cached via `@lru_cache`:
- Embeddings (single load)
- Pinecone vector store
- BM25 index (built once at startup)
- Compressor pipeline
- LLM instances
- RAG chain

### Session Management
- Session ID generated via UUID
- History capped at 20 messages
- Cookie-safe memory limits

### Error Handling
- Graceful degradation if BM25 unavailable
- Timeout handling (30s for API calls)
- User-friendly error messages
- Full stack traces logged to file

### Logging
- File logging: `app.log`
- Console output (UTF-8 safe)
- Request-scoped logs for UI display

---

## 11. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve chat UI |
| `/get` | POST | Process user message, return response + logs |
| `/clear` | POST | Clear session history |

---

## 12. Conclusion: Production Readiness

By combining:
- **Pinecone** for scalable vector storage
- **Groq** for lightning-fast LPU inference
- **BGE** for compact, efficient embeddings
- **LangChain** for modular RAG orchestration
- **Ragas** for continuous quality monitoring
- **Real-time logs** for full pipeline visibility

This system is built to scale from a prototype to a professional-grade medical assistant with complete observability.

---

## 13. Technology Stack Summary

| Component | Technology |
|-----------|------------|
| Framework | Flask |
| Frontend | HTML/CSS/JS (jQuery) |
| Embeddings | BAAI/bge-small-en-v1.5 |
| Vector DB | Pinecone |
| LLM | Groq (Llama 3.3 70B) |
| Query Rewrite | Groq (Llama 3.1 8B) |
| Reranker | Cross-Encoder ms-marco-MiniLM-L-6-v2 |
| PDF Processing | PyMuPDF + NLTK |
| Token Counting | tiktoken |
| Evaluation | Ragas |
