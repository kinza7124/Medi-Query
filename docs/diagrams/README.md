# 🎨 Diagrams - Complete Visual Documentation

This folder contains comprehensive visual documentation of the Medical AI Chatbot system architecture, including Mermaid diagrams, PNG images, and detailed explanations.

## 📑 Diagrams Index

### 1. **RAG Pipeline Sequence Diagram**
- **File**: [RAG_SEQUENCE_DIAGRAM.md](RAG_SEQUENCE_DIAGRAM.md)
- **Purpose**: End-to-end user query flow through the RAG system
- **Level**: Detailed step-by-step sequence
- **Audience**: Developers, QA Engineers
- **Shows**:
  - User input through browser
  - Query rewriting with context
  - Document retrieval (MMR + reranking)
  - Response generation (LLM)
  - Session memory management
  - Performance breakdown (response timing by component)

**View it**: [Open RAG_SEQUENCE_DIAGRAM.md](RAG_SEQUENCE_DIAGRAM.md)

---

### 2. **RAG System Architecture Diagram**
- **File**: [RAG_ARCHITECTURE_DIAGRAM.md](RAG_ARCHITECTURE_DIAGRAM.md)
- **Purpose**: Complete end-to-end system architecture
- **Level**: Comprehensive high-level overview
- **Audience**: Architects, Tech Leads, Project Managers
- **Shows**:
  - Document indexing pipeline
  - Query processing pipeline
  - Document retrieval pipeline
  - Response generation pipeline
  - External APIs (Groq, Pinecone, HuggingFace)
  - Deployment infrastructure (Docker, AWS EC2)
  - Data flow across all components
  - Configuration parameters
  - Error handling strategy

**View it**: [Open RAG_ARCHITECTURE_DIAGRAM.md](RAG_ARCHITECTURE_DIAGRAM.md)

---

### 3. **CI/CD Pipeline Architecture**
- **File**: [CICD_PIPELINE_DIAGRAM.md](CICD_PIPELINE_DIAGRAM.md)
- **Purpose**: Continuous Integration and Deployment workflow
- **Level**: DevOps/deployment focus
- **Audience**: DevOps Engineers, Backend Developers
- **Shows**:
  - Developer local workflow
  - GitHub push trigger
  - CI stage: Build, test, push to ECR
  - CD stage: Pull, deploy to EC2
  - AWS infrastructure (ECR, EC2, Docker)
  - External API dependencies
  - Failure handling & rollback
  - Secrets management
  - Health check endpoints
  - Complete GitHub Actions workflow YAML

**View it**: [Open CICD_PIPELINE_DIAGRAM.md](CICD_PIPELINE_DIAGRAM.md)

---

### 4. **PNG Image Files** (Original Diagrams)
Located in this folder for reference:

| File | Description |
|------|------------|
| `rag_sequence_diagram.png` | Original PNG of RAG sequence |
| `rag_complete_architecture.png` | Original PNG of RAG architecture |
| `cicd_architecture.png` | Original PNG of CI/CD pipeline |

---

## 🔍 Diagram Quick Comparison

### When to Use Each Diagram

| Need | Diagram | Why |
|------|---------|-----|
| **Understand query flow** | Sequence Diagram | Shows step-by-step timing and interactions |
| **See full system** | Architecture Diagram | Shows all components and connections |
| **Deploy/maintain app** | CI/CD Pipeline | Shows automated deployment process |
| **Train team member** | Start with Architecture, then Sequence | Broad overview first, then deep dive |
| **Debug slow response** | Sequence + Architecture | Identify bottleneck component |
| **Add new feature** | Architecture | Determine where to integrate |
| **Fix broken deployment** | CI/CD Pipeline | Understand where failure occurred |

---

## 📊 Component Relationships

### How Diagrams Work Together

```
RAG Architecture Diagram (High-level system view)
        ↓
        Describes 4 main pipelines:
        ├─ Document Indexing
        ├─ Query Processing
        ├─ Document Retrieval
        └─ Response Generation
        
        ↓ Details
        
RAG Sequence Diagram (Step-by-step execution)
        Shows how components interact when
        a user submits a query

        ↓ Deployment
        
CI/CD Pipeline Diagram (Automation)
        Shows how code changes move
        from dev → testing → production
```

---

## 🎓 Reading Guide by Role

### For New Team Members
1. Start: [RAG_ARCHITECTURE_DIAGRAM.md](RAG_ARCHITECTURE_DIAGRAM.md) - Understand the system
2. Next: [RAG_SEQUENCE_DIAGRAM.md](RAG_SEQUENCE_DIAGRAM.md) - See how it works in action
3. Finally: [CICD_PIPELINE_DIAGRAM.md](CICD_PIPELINE_DIAGRAM.md) - How to deploy changes

### For Developers
- **Reference**: [RAG_SEQUENCE_DIAGRAM.md](RAG_SEQUENCE_DIAGRAM.md) - Understand component APIs
- **Extension**: [RAG_ARCHITECTURE_DIAGRAM.md](RAG_ARCHITECTURE_DIAGRAM.md) - Add new components
- **Integration**: [CICD_PIPELINE_DIAGRAM.md](CICD_PIPELINE_DIAGRAM.md) - Push changes confidently

### For DevOps/Infra Team
- **Primary**: [CICD_PIPELINE_DIAGRAM.md](CICD_PIPELINE_DIAGRAM.md) - Understand deployment
- **Context**: [RAG_ARCHITECTURE_DIAGRAM.md](RAG_ARCHITECTURE_DIAGRAM.md) - Understand infrastructure needs

### For QA Engineers
- **Test Design**: [RAG_SEQUENCE_DIAGRAM.md](RAG_SEQUENCE_DIAGRAM.md) - Know what to test
- **Edge Cases**: [RAG_ARCHITECTURE_DIAGRAM.md](RAG_ARCHITECTURE_DIAGRAM.md) - Find failure points

### For Project Managers
- **Overview**: [RAG_ARCHITECTURE_DIAGRAM.md](RAG_ARCHITECTURE_DIAGRAM.md) - See full scope
- **Timeline**: [CICD_PIPELINE_DIAGRAM.md](CICD_PIPELINE_DIAGRAM.md) - Understand deployment frequency

---

## 🔑 Key Concepts by Diagram

### Sequence Diagram Concepts
- **Session Memory**: Last 10 chat exchanges for context
- **Query Rewriting**: Resolves pronouns using history
- **MMR Retrieval**: Balances relevance vs diversity (lambda_mult=0.5)
- **Cross-Encoder**: Reranks documents (top-4 final)
- **Context-Only Mode**: LLM answers only from retrieved context
- **Performance**: ~4.2s total (SLA < 5s)

### Architecture Diagram Concepts
- **Document Indexing**: One-time setup with 800-char overlap chunks
- **Query Processing**: Detects greetings, rewrites complex queries
- **4-Stage Pipeline**: Process → Retrieve → Rerank → Generate
- **External APIs**: Groq (LLM), Pinecone (vectors), HuggingFace (embeddings)
- **Fallback**: Smaller model (Llama 3.1 8B) if main model times out
- **Safety**: Medical disclaimers on all health responses

### CI/CD Concepts
- **Trigger**: Push to main triggers automated workflow
- **Build**: Docker build + pytest + ECR push (~2-3 min)
- **Deploy**: Pull from ECR, run on EC2, health check (~1 min)
- **Secrets**: API keys from GitHub encrypted secrets
- **Rollback**: Auto-revert if health check fails
- **Frequency**: 1-5 deployments per day (continuous delivery)

---

## 📈 System Metrics Summary

### Performance Targets
| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Response Time | < 5s | 4.2s | ✅ Excellent |
| Answer Relevancy | > 85% | 92.36% | ✅ Excellent |
| Answer Relevance | > 85% | 92.36% | ✅ Excellent |
| Context Recall | > 70% | 66.67% | ⚠️ Good |
| Context Precision | > 60% | 55.56% | ⚠️ Acceptable |

### Infrastructure Specs
| Component | Specification |
|-----------|--------------|
| **Embedding Model** | all-MiniLM-L6-v2 (384 dimensions) |
| **Main LLM** | Llama 3.3 70B (Groq API) |
| **Fallback LLM** | Llama 3.1 8B (Groq API) |
| **Cross-Encoder** | ms-marco-MiniLM-L-6-v2 |
| **Vector Database** | Pinecone with cosine similarity |
| **Frame Work** | LangChain with Flask |
| **Deployment** | Docker on AWS EC2 (Port 8080) |
| **Health Check** | `/health` endpoint (5s interval) |

---

## 🔄 Workflow Examples

### Example 1: User Query Flow
```
User: "What is diabetes?"
  ↓
[Session Memory] - Empty (new session)
  ↓
[Query Rewriting] - No pronouns, query unchanged
  ↓
[Embedding] - Convert to 384-dim vector
  ↓
[Retrieval] - MMR search returns 10 docs
  ↓
[Reranking] - Cross-encoder selects top-4
  ↓
[Response] - "Diabetes is a metabolic disorder..."
  ↓
[Memory Update] - Store Q&A in session
```

### Example 2: Contextual Follow-up
```
User: "How to treat it?"
  ↓
[Session Memory] - Retrieved: {"What is diabetes?", "Diabetes is..."}
  ↓
[Query Rewriting] - "treat it?" → "How to treat diabetes?"
  ↓
[Embedding] - Convert rewritten query to vector
  ↓
[Retrieval] - Search for diabetes + treatment
  ↓
[Reranking] - Get top-4 treatment-focused docs
  ↓
[Response] - "Treatment for diabetes includes..."
```

### Example 3: Non-Medical Query
```
User: "Hi, how are you?"
  ↓
[Session Memory] - Retrieved (not relevant)
  ↓
[Greeting Detection] - ✓ Is greeting
  ↓
[Skip Retrieval] - Don't search vector DB
  ↓
[Predefined Response] - "Hello! I'm a medical AI chatbot..."
```

---

## 🛠️ Common Tasks

### **Task: Add a new medical topic**
→ See [RAG_ARCHITECTURE_DIAGRAM.md](RAG_ARCHITECTURE_DIAGRAM.md) `Document Indexing Pipeline` section

### **Task: Improve response speed**
→ See [RAG_SEQUENCE_DIAGRAM.md](RAG_SEQUENCE_DIAGRAM.md) `Performance Metrics` section

### **Task: Deploy a code change**
→ See [CICD_PIPELINE_DIAGRAM.md](CICD_PIPELINE_DIAGRAM.md) `CI/CD Pipeline Workflow` section

### **Task: Debug slow retrieval**
→ See [RAG_SEQUENCE_DIAGRAM.md](RAG_SEQUENCE_DIAGRAM.md) + [RAG_ARCHITECTURE_DIAGRAM.md](RAG_ARCHITECTURE_DIAGRAM.md) retrieval sections

### **Task: Add observability/monitoring**
→ See [CICD_PIPELINE_DIAGRAM.md](CICD_PIPELINE_DIAGRAM.md) `Pipeline Monitoring` section

---

## 📚 Related Documentation

| Document | Purpose | Location |
|----------|---------|----------|
| **PROJECT_SUMMARY.md** | High-level project overview | `/docs/` |
| **RAG_Evaluation_Report.md** | Detailed metrics & test results | `/docs/` |
| **SRS_Report_IEEE.md** | Software requirements specification | `/docs/` |
| **Testing_Documentation.md** | QA test plans & procedures | `/docs/` |
| **RAG_OPTIMIZATION_GUIDE.md** | Improvement strategies | `/` |
| **QUICK_START.md** | Getting started guide | `/` |

---

## 🎨 Diagram File Formats

### Mermaid Format
- **Why**: Platform-independent, version control friendly
- **View**: In GitHub, VS Code, Mermaid Live Editor
- **Edit**: Plain text, easy to update
- **Export**: Can generate PNG/SVG if needed

### PNG Format
- **Why**: Legacy reference, presentation-ready
- **Location**: Same folder with `.png` extension
- **Note**: Consider updating screenshots with new versions

---

## ✅ Diagram Quality Checklist

Each diagram should have:
- [x] Clear title and purpose
- [x] Legend/color coding
- [x] Component labels
- [x] Data flow arrows
- [x] Performance metrics (where relevant)
- [x] Error handling paths
- [x] External dependencies
- [x] Configuration parameters
- [x] Success/failure scenarios
- [x] Detailed text explanation

---

## 📞 Questions?

- **Architecture**: See `RAG_ARCHITECTURE_DIAGRAM.md`
- **Execution**: See `RAG_SEQUENCE_DIAGRAM.md`
- **Deployment**: See `CICD_PIPELINE_DIAGRAM.md`
- **General Help**: Check related docs in `/docs/` folder

---

**Last Updated**: May 4, 2026  
**Version**: 2.0 (Mermaid-enhanced)  
**Status**: Complete ✅

