# RAG System Architecture Diagram (Mermaid)

This diagram shows the complete end-to-end system architecture including document indexing, query processing, and response generation pipelines.

## Complete System Architecture

```mermaid
graph TB
    subgraph DocumentIndexing["📚 DOCUMENT INDEXING PIPELINE"]
        direction LR
        D1["Medical PDFs<br/>& Documents"] -->|Load| D2["Document Loader<br/>(PyPDF)"]
        D2 -->|Parse| D3["Raw Text<br/>Extraction"]
        D3 -->|Split| D4["Context-Aware<br/>Chunking<br/>chunk_size=800<br/>overlap=100"]
        D4 -->|Generate| D5["Embedding<br/>all-MiniLM-L6-v2<br/>384-dim vectors"]
        D5 -->|Store| D6[("Pinecone Vector DB<br/>(Indexed & Ready)")]
    end

    subgraph QueryProcessing["🔍 QUERY PROCESSING PIPELINE"]
        direction TB
        Q1["User Query<br/>(Browser)"] 
        Q2["Flask Session<br/>Memory<br/>(Last 10 exchanges)"]
        Q3{Greeting or<br/>Personal?}
        Q4["Query Rewriter<br/>Llama 3.3 70B<br/>Pronoun Resolution"]
        Q5["Query Embedding<br/>HuggingFace<br/>384-dim vector"]
        
        Q1 --> Q2
        Q2 --> Q3
        Q3 -->|Yes| Q9["Predefined<br/>Response"]
        Q3 -->|No| Q4
        Q4 -->|Rewritten<br/>Query| Q5
        
    end

    subgraph Retrieval["📖 DOCUMENT RETRIEVAL PIPELINE"]
        direction TB
        R1["Query Vector"] 
        R2["MMR Retrieval<br/>k=10, fetch_k=30<br/>lambda_mult=0.5"]
        R3["10 Candidate<br/>Documents"]
        R4["Cosine Similarity<br/>Ranking"]
        R5["Cross-Encoder<br/>Reranker<br/>ms-marco-MiniLM-L-6-v2"]
        R6["Top-4<br/>Documents"]
        R7["Contextual<br/>Compression<br/>(Remove noise)"]
        R8["Merged<br/>Context<br/>(Final)"]
        
        R1 --> R2
        R2 --> R3
        R3 --> R4
        R4 --> R5
        R5 --> R6
        R6 --> R7
        R7 --> R8
    end

    subgraph ResponseGeneration["💬 RESPONSE GENERATION PIPELINE"]
        direction TB
        G1["Optimized Query<br/>+ Context<br/>+ History"]
        G2["System Prompt<br/>Context-Only Mode"]
        G3["Prompt Builder<br/>Format injection safety"]
        G4["Llama 3.3 70B<br/>Groq API<br/>temperature=0"]
        G5["Generated<br/>Response<br/>(Raw)"]
        G6["Answer Cleaner<br/>Remove meta-references"]
        G7["Safety Check<br/>Add Medical Disclaimer"]
        G8["Final<br/>Response"]
        G9["Update Session<br/>Memory<br/>(Last 10 exchanges)"]
        
        G1 --> G2
        G2 --> G3
        G3 --> G4
        G4 --> G5
        G5 --> G6
        G6 --> G7
        G7 --> G8
        G8 --> G9
    end

    subgraph ExternalAPIs["🔗 EXTERNAL APIs & SERVICES"]
        API1["Groq LLM<br/>API"]
        API2["Pinecone<br/>Vector DB API"]
        API3["HuggingFace<br/>Model Hub"]
    end

    subgraph Infrastructure["☁️ DEPLOYMENT INFRASTRUCTURE"]
        INF1["Flask App<br/>Port 5000<br/>(Development)"]
        INF2["Gunicorn<br/>Port 8080<br/>(Production)"]
        INF3["Docker<br/>Container"]
        INF4["AWS EC2<br/>Instance"]
        INF5["/health<br/>Endpoint"]
    end

    %% Connections between pipelines
    Q5 --> R1
    R8 --> G1
    Q9 --> G8

    %% External API connections
    Q4 -.->|API Call| API1
    D5 -.->|Send vectors| API2
    R2 -.->|Query| API2
    D5 -.->|Download model| API3
    Q5 -.->|Embed query| API3
    G4 -.->|Generate answer| API1

    %% Infrastructure connections
    Q1 -.->|Browser request| INF1
    INF1 --> INF3
    INF3 --> INF2
    INF2 --> INF4
    INF5 -.->|Health check| INF4

    %% Styling
    classDef pipeline fill:#1a1a2e,stroke:#0f3460,stroke-width:3px,color:#fff
    classDef process fill:#16213e,stroke:#0f3460,stroke-width:2px,color:#eee
    classDef external fill:#e94560,stroke:#d4144d,stroke-width:2px,color:#fff
    classDef infra fill:#0a9396,stroke:#05757f,stroke-width:2px,color:#fff
    classDef decision fill:#ffd60a,stroke:#ffc300,stroke-width:2px,color:#000
    classDef data fill:#386641,stroke:#2d6a4f,stroke-width:2px,color:#fff

    class DocumentIndexing,QueryProcessing,Retrieval,ResponseGeneration pipeline
    class D1,D2,D3,D4,D5,D6,Q1,Q2,Q4,Q5,R1,R2,R3,R4,R5,R6,R7,R8,G1,G2,G3,G4,G5,G6,G7,G8,G9 process
    class Q3 decision
    class API1,API2,API3 external
    class INF1,INF2,INF3,INF4,INF5 infra
```

## Detailed Component Breakdown

### 📚 Document Indexing Pipeline

**Purpose**: Prepare medical documents for efficient semantic search

| Component | Details |
|-----------|---------|
| **Input** | PDF files, Medical documents |
| **Processing** | Load → Parse → Extract → Chunk → Embed |
| **Chunk Strategy** | 800 characters with 100-char overlap for context preservation |
| **Embedding Model** | `all-MiniLM-L6-v2` (384 dimensions) |
| **Vector Store** | Pinecone with cosine similarity metric |
| **Frequency** | One-time during setup, reindex as needed |

### 🔍 Query Processing Pipeline

**Purpose**: Prepare user queries for retrieval while maintaining conversational context

| Component | Details |
|-----------|---------|
| **Session Memory** | Stores last 10 chat exchanges (max 20 messages) |
| **Greeting Detection** | Identifies non-medical queries ("Hi", "What are you?", etc.) |
| **Query Rewriting** | Uses Llama 3.3 70B to resolve pronouns and expand queries |
| **Example** | "How to treat it?" → "How to treat diabetes?" (from context) |
| **Embedding** | Converts rewritten query to 384-dimensional vector |

### 📖 Document Retrieval Pipeline

**Purpose**: Find the most relevant documents for the user query

| Component | Details |
|-----------|---------|
| **MMR Retrieval** | Maximum Marginal Relevance with k=10, fetch_k=30, lambda_mult=0.5 |
| **Candidate Pool** | 30 initial candidates scored by cosine similarity |
| **Output** | Top 10 documents balancing relevance and diversity |
| **Cross-Encoder** | Re-ranks top 10, returns top-4 with higher precision |
| **Compression** | Removes noise and irrelevant sections from final context |

**Lambda Parameters**: 
- Higher `lambda_mult` (closer to 1): More diversity, less relevance
- Lower `lambda_mult` (closer to 0): More relevance, less diversity
- Our setting (0.5): Good balance between precision and coverage

### 💬 Response Generation Pipeline

**Purpose**: Generate accurate, safe, context-grounded medical responses

| Component | Details |
|-----------|---------|
| **System Prompt** | "Answer only from the provided context" (strict mode) |
| **Context** | Top-4 reranked documents from retrieval |
| **Chat History** | Last exchange for reference (not substitution) |
| **Model** | Llama 3.3 70B, temperature=0 for deterministic output |
| **Safety** | Medical disclaimer appended to all health responses |
| **Memory Update** | User query + Assistant answer stored for next exchange |

### 🔗 External APIs

| API | Purpose | Rate Limits | Cost Model |
|-----|---------|------------|-----------|
| **Groq LLM** | Query rewriting & response generation | Depends on plan | Pay-per-token |
| **Pinecone** | Vector database storage & search | Depends on tier | Managed service |
| **HuggingFace** | Embedding model & cross-encoder | Free tier available | Open-source models |

### ☁️ Infrastructure

| Component | Development | Production |
|-----------|------------|-----------|
| **Application Server** | Flask (Port 5000) | Gunicorn (Port 8080) |
| **Containerization** | Docker image | Docker image |
| **Deployment** | Local or EC2 | AWS EC2 (t2.micro/t3.small) |
| **Health Check** | `/health` endpoint | Monitored by load balancer |
| **Logging** | File + Console | File + CloudWatch (optional) |

## Data Flow Summary

```
User Input
    ↓
Session Context Retrieval
    ↓
Greeting Detection
    ├─ YES → Predefined Response
    └─ NO → Query Rewriting
         ↓
    Query Embedding
         ↓
    Document Retrieval (MMR)
         ↓
    Cross-Encoder Reranking
         ↓
    Context Compression
         ↓
    Response Generation (Groq LLM)
         ↓
    Safety & Cleaning
         ↓
    Session Memory Update
         ↓
    Final Response to User
```

## Configuration Parameters

| Parameter | Value | Impact |
|-----------|-------|--------|
| `chunk_size` | 800 | Larger = more context per chunk, slower processing |
| `chunk_overlap` | 100 | Overlap prevents information loss at boundaries |
| `embedding_dim` | 384 | Balance between accuracy and speed |
| `k` (MMR) | 10 | Initial candidates, higher = broader search |
| `fetch_k` (MMR) | 30 | Pool size for diversity calculation |
| `lambda_mult` | 0.5 | 0.5 = balance relevance and diversity |
| `top_n` (reranker) | 4 | Final context size, fewer = less noise |
| `max_session_messages` | 12 | Max messages in session (prevents cookie bloat) |
| `temperature` | 0 | Deterministic responses, no randomness |

## Safety & Error Handling

| Scenario | Handling |
|----------|----------|
| **No relevant context** | Return "I don't have information..." |
| **Groq API timeout** | Fallback to smaller model (Llama 3.1 8B) |
| **Embedding service down** | Use keyword search fallback |
| **Session memory overflow** | Truncate to most recent messages |
| **Malicious prompt injection** | System prompt prevents context escape |

## Expected Performance

| Metric | Target | Actual (Latest) | Status |
|--------|--------|-----------------|--------|
| Answer Relevancy | > 85% | 92.36% | ✅ Excellent |
| Context Recall | > 70% | 66.67% | ⚠️ Moderate |
| Context Precision | > 60% | 55.56% | ⚠️ Needs Work |
| Response Time | < 5s | 4.2s | ✅ Excellent |
| Uptime SLA | > 99% | TBD | Monitoring |

## Future Improvements

1. **Multimodal Support**: Add image/diagram analysis
2. **Advanced Caching**: Cache frequent query results
3. **Real-time Updates**: Stream responses instead of batch
4. **Multi-language**: Support non-English medical queries
5. **Fact-checking**: Additional verification layer for medical accuracy
