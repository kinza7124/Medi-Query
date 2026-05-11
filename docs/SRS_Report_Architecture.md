# System Architecture Diagrams

**Group:** Kinza, Laiba, sanjana 
**Date:** April 29, 2026  

---

## 1. RAG Pipeline Sequence Diagram

![RAG Pipeline Sequence Diagram](diagrams/rag_sequence_diagram.png)

**Description:** This sequence diagram shows the complete data flow of the RAG pipeline from user query to response generation. It includes:
- User Browser to Flask Server interaction
- Session Memory retrieval
- Query Rewrite LLM (pronoun resolution)
- HuggingFace embedding generation (384-dim)
- Pinecone Vector DB similarity search (k=10)
- Cross-Encoder reranking (top 4 documents)
- Groq LLM response generation
- History update and response delivery

---

## 2. Complete RAG Pipeline Architecture

![Complete RAG Pipeline Architecture](diagrams/rag_complete_architecture.png)

**Description:** This comprehensive architecture diagram shows three main pipelines:

### Document Indexing Pipeline (Top Section)
- Medical PDFs → Document Loader → Hybrid Chunking
- Parameters: chunk_size=800, chunk_overlap=100, 8845 chunks total
- Embedding Model: all-MiniLM-L6-v2 (384 dimensions)
- Vector Database: Pinecone with Cosine Similarity
- BM25 Index: Built from same chunks for hybrid retrieval

### Query Processing Pipeline (Middle Section)
- User Query → Flask App Session Memory
- Greeting/Personal check → Query Rewriter (Llama 3.1 8B)
- Intent Detection → Metadata Filtering (optional)
- Hybrid Retriever → BM25 (40%) + Dense MMR (60%) ensemble
- Cross-Encoder Reranker (ms-marco-MiniLM-L-6-v2, top_n=6)
- Contextual Compression → Retrieved Context

### Response Generation (Right Section)
- Prompt Builder (System + Context + History)
- Strict Context-Only Policy (no meta-commentary, no external knowledge)
- Llama 3.3 70B generates response
- **Response Restructuring Pipeline:**
  1. Sentence-level classification (content vs disclaimer vs emergency)
  2. Disclaimers moved to end automatically
  3. Deduplication of repeated disclaimer phrases
- Answer Cleaner (remove "According to context" framing)
- Safety Check (add disclaimer if missing)
- Session Memory (last 10 exchanges)

---

## 3. CI/CD Pipeline Architecture

![CI/CD Pipeline Architecture](diagrams/cicd_architecture.png)

**Description:** This diagram shows the complete deployment workflow:

### Developer Workflow (Blue)
- Git Push to main branch (Trigger)
- Dockerfile (Python 3.10 + App) as Build Context

### GitHub Actions CI/CD (Purple)
**CI: Build & Push**
- Build Docker Image
- Push to Amazon ECR

**CD: Deploy**
- AWS EC2 Instance (Self-hosted Runner)
- Docker Run on Port 8080

### AWS Infrastructure (Green)
- Amazon ECR (Container Registry)
- EC2 Instance (t2.micro/t3.small)

### External APIs (Pink)
- Groq API (LLM Inference)
- Pinecone API (Vector Search)

---

## Key Configuration Parameters

| Component | Configuration |
|-----------|---------------|
| Chunk Size | 800 characters |
| Chunk Overlap | 100 characters |
| Embedding Dimensions | 384 (all-MiniLM-L6-v2) |
| Ensemble Weights | BM25: 40%, Dense: 60% |
| Initial Retrieval | k=10 (hybrid BM25 + Dense) |
| Final Documents | top_n=6 (Cross-Encoder) |
| Metadata Filtering | Section-based intent matching |
| Query Rewrite Model | Llama 3.1 8B |
| Answer Model | Llama 3.3 70B |
| Session Memory | 10 exchanges (20 messages) |
| Frontend Timeout | 60 seconds |
| Deployment Port | 8080 |
| Response Restructuring | Automatic disclaimer repositioning |

---

*These diagrams provide a visual representation of the Medical AI Chatbot system architecture.*
