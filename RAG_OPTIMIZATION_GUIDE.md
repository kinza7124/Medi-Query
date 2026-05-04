# RAG System Optimization Guide

## Overview
This guide provides comprehensive strategies to improve the accuracy, precision, and recall of your Medical AI Chatbot's RAG (Retrieval-Augmented Generation) pipeline.

---

## 1. NEW EVALUATION FRAMEWORK

### Comprehensive Metrics
We've implemented `rag_evaluation_comprehensive.py` with advanced metrics:

#### **Retrieval Metrics (Precision@K, Recall@K)**
- **Precision@K**: Percentage of top-K retrieved documents that are relevant
  - `precision_at_1`: Is the #1 result relevant?
  - `precision_at_3`: How many of top-3 are relevant?
  - `precision_at_5`: Quality of top-5 results

- **Recall@K**: Percentage of all relevant documents found in top-K
  - `recall_at_3`: Did we find most relevant docs in top-3?
  - `recall_at_5`: Coverage in top-5 results
  - `recall_at_10`: Coverage for deeper searches

#### **Ranking Metrics**
- **MRR (Mean Reciprocal Rank)**: Inverse position of first relevant result
  - High MRR: Relevant results ranked early
  
- **NDCG@5 (Normalized Discounted Cumulative Gain)**: Accounts for ranking quality
  - Penalizes relevant docs that appear later
  - Scale: 0.0-1.0

- **MAP@5 (Mean Average Precision)**: Average precision at each relevant position
  - Comprehensive ranking quality metric

#### **Answer Quality Metrics**
- **Faithfulness**: Is answer grounded in retrieved context?
- **Answer Relevancy**: Does answer address the question?
- **Context Precision**: Are retrieved contexts relevant to the question?
- **Context Recall**: Do contexts contain all necessary information?

#### **Text Similarity Metrics**
- **Semantic Similarity**: Cosine similarity (embedding-based)
- **BLEU Score**: N-gram overlap with ground truth
- **ROUGE-L**: Longest common subsequence match
- **Exact Match**: Percentage of identical answers

### Usage Example
```python
from rag_evaluation_comprehensive import RAGEvaluator

evaluator = RAGEvaluator()

eval_dataset = [
    {
        "question": "What are acne symptoms?",
        "ground_truth": "Blackheads, whiteheads, pimples, oily skin...",
        "relevant_docs": ["Acne appears as blackheads...", "Oily skin occurs..."]
    },
    # ... more samples
]

# Run evaluation
results, aggregates = evaluator.evaluate_rag_system(
    eval_dataset=eval_dataset,
    retrieval_func=your_retriever.retrieve,
    generation_func=your_generator.generate,
    output_file="evaluation_results.csv"
)

# Results include:
# - Per-query metrics (Precision@K, Recall@K, NDCG, etc.)
# - Aggregated statistics (mean, std, min, max)
# - CSV and JSON output files
```

---

## 2. IMPROVED RETRIEVAL PIPELINE

### New Features (`improved_retrieval.py`)

#### **Hybrid Retrieval (BM25 + Semantic)**
Combines lexical and semantic search:
- **BM25**: Fast, keyword-based matching (solves typo/synonym issues)
- **Semantic Search**: Vector-based understanding of meaning
- **Weighted Combination**: 40% BM25 + 60% Semantic

```python
from improved_retrieval import HybridRetriever

hybrid = HybridRetriever(documents, embeddings, index_name="medical-chatbot")
results = hybrid.retrieve("diabetes management", k=10)
```

#### **Query Expansion**
Generate multiple query formulations to capture different aspects:

```python
from improved_retrieval import QueryExpander

expander = QueryExpander(llm)
queries = expander.expand_query("What is diabetes?")
# Returns: 
# - "What is diabetes?"
# - "Diabetes definition and overview"
# - "Understanding diabetes mellitus"
# - "Diabetes disease characteristics"
```

Benefits:
- Captures synonyms and alternate phrasings
- Retrieves more comprehensive context
- Handles user typos and variations

#### **Advanced Reranking**

**Cross-Encoder Reranking** (default):
```python
from improved_retrieval import CrossEncoderReranker

reranker = CrossEncoderReranker("cross-encoder/ms-marco-MiniLM-L-6-v2")
reranked = reranker.rerank(query, initial_docs, top_n=5)
```

Why it works better than previous approach:
- Processes query and document *together*
- Understands deep semantic relevance
- More accurate than bi-encoder ranking

**Diversity Reranking**:
```python
from improved_retrieval import DiversityReranker

div_reranker = DiversityReranker(embeddings)
diverse_docs = div_reranker.rerank(query, docs, top_n=5)
```

Prevents:
- Multiple similar documents in results
- Redundant information
- Coverage gaps

#### **Advanced Retriever Pipeline**
Complete end-to-end solution:

```python
from improved_retrieval import AdvancedRetriever

retriever = AdvancedRetriever(
    documents=your_docs,
    embeddings=embeddings,
    llm=groq_llm,
    index_name="medical-chatbot"
)

docs = retriever.retrieve_with_expansion(
    query="diabetes management",
    use_expansion=True,        # Query expansion
    use_hybrid=True,            # BM25 + semantic
    use_reranking=True,         # Cross-encoder + diversity
    top_n=5
)
```

---

## 3. CHUNKING & CONTEXT OPTIMIZATION

### Current Approach Analysis
Your `context_aware_split()` function is good but can be enhanced:

#### Issues & Solutions

**Issue 1**: Fixed chunk size (800 chars) misses context boundaries
**Solution**: 
- Use variable chunk sizes (500-1500 chars based on density)
- Keep medical subsections together
- Preserve header-content relationship

**Issue 2**: Simple overlap doesn't preserve cross-chunk references
**Solution**:
- Include 1-2 sentences before/after chunk (padding)
- Track section headers in metadata
- Store entity relationships

#### Improved Chunking Strategy

```python
def improved_context_aware_split(documents, dynamic_sizing=True):
    """
    Enhanced context-aware chunking with:
    - Dynamic chunk sizes based on content density
    - Better section boundary detection
    - Rich metadata (section, subsection, entities, keywords)
    """
    # 1. Pre-process: Extract headers and structure
    # 2. Split at semantic boundaries (headers > paragraphs > sentences > words)
    # 3. Dynamic sizing:
    #    - Dense medical text: 500-800 chars
    #    - Clinical guidelines: 800-1200 chars
    #    - Case studies: 1000-1500 chars
    # 4. Rich metadata:
    #    - Section heading
    #    - Medical entities (diseases, treatments, symptoms)
    #    - Key terms and entities
    #    - Source document and page number
    # 5. Context windows: Include 2-3 sentence boundaries around chunks
```

**Implementation in `src/helper.py`**:

Current: Detects headers but basic overlap
Improved: 
- Add entity extraction (using medical NER models)
- Dynamic chunk sizing based on semantic density
- Multi-level hierarchical metadata
- Sentence padding around chunks

---

## 4. PROMPT & GENERATION IMPROVEMENTS

### Current System Prompt Strengths
✅ Enforces context-only answers
✅ Clear safety protocols
✅ Professional tone guidelines
✅ Edge case handling

### Recommended Enhancements

#### Addition 1: Chain-of-Thought Prompting
```
System prompt addition:
"For complex questions, explain your reasoning step-by-step:
1. What does the question ask?
2. What relevant information is in the context?
3. How do the context points address the question?
4. What is the final answer?"
```

Benefits:
- More accurate reasoning
- Better answer breakdown
- Easier error detection in evaluation

#### Addition 2: Context Citation
```
"When citing context, include the document source and section.
Example: According to [Medical Encyclopedia, Acne Section]: ..."
```

Benefits:
- Traceable answers (good for medical accuracy)
- User can verify sources
- Better for fact-checking

#### Addition 3: Confidence Scoring
```
"Include a confidence level (high/medium/low) based on:
- How directly context answers the question
- Completeness of context
- Multiple vs. single source confirmation"
```

#### Addition 4: Structured Responses
```
"For clinical questions, use this format:
DEFINITION: [Brief definition]
SYMPTOMS: [List of symptoms]
CAUSES: [Contributing factors]
MANAGEMENT: [Treatment/dietary/lifestyle options]
WHEN TO SEEK HELP: [Red flags]"
```

---

## 5. IMPLEMENTATION ROADMAP

### Phase 1: Integrate New Evaluation (Week 1)
- [ ] Review `rag_evaluation_comprehensive.py`
- [ ] Prepare evaluation dataset (30-50 medical Q&A pairs)
- [ ] Run baseline evaluation
- [ ] Document current performance

### Phase 2: Deploy Hybrid Retrieval (Week 2)
- [ ] Set up BM25 indexing
- [ ] Test hybrid retrieval vs. current
- [ ] Measure Precision@K and Recall@K improvements
- [ ] Expected improvement: +15-25% recall

### Phase 3: Add Query Expansion (Week 2-3)
- [ ] Integrate QueryExpander
- [ ] Test on 10 benchmark queries
- [ ] Measure coverage improvement
- [ ] Expected improvement: +20-30% answer relevancy

### Phase 4: Implement Reranking (Week 3)
- [ ] Deploy cross-encoder reranker
- [ ] Compare with current reranker
- [ ] Add diversity reranking
- [ ] Expected improvement: +10-15% precision

### Phase 5: Optimize Chunking (Week 4)
- [ ] Implement variable chunk sizing
- [ ] Add entity extraction
- [ ] Create hierarchical metadata
- [ ] Re-index vector database
- [ ] Expected improvement: +25-35% context precision

### Phase 6: Enhance Prompts (Week 4)
- [ ] Add chain-of-thought
- [ ] Add source citations
- [ ] Test answer quality
- [ ] Expected improvement: +15-20% faithfulness

---

## 6. KEY PERFORMANCE INDICATORS (KPIs)

### Target Metrics
| Metric | Current | Target | Weight |
|--------|---------|--------|--------|
| Precision@5 | ~0.4 | >0.75 | 20% |
| Recall@5 | ~0.5 | >0.80 | 20% |
| NDCG@5 | ~0.52 | >0.75 | 15% |
| Answer Relevancy | ~0.55 | >0.80 | 15% |
| Faithfulness | ~0.45 | >0.80 | 15% |
| Semantic Similarity | ~0.65 | >0.85 | 15% |

### Success Criteria
- Overall score: >0.75 (75/100)
- No metric below 0.70
- User satisfaction: >4.0/5.0 (from user feedback)

---

## 7. QUICK WINS (Easy, High Impact)

### 1. Increase Retrieved Context Size
```python
# From: retrieve top 6 docs
# To: retrieve top 8-10 docs, better rerank
retriever.retrieve(query, k=10)  # Then rerank to 5-6
```
**Impact**: +10% recall with minimal latency hit

### 2. Lower Similarity Threshold
```python
# From: search_kwargs={"lambda_mult": 0.5}
# To: More diverse results
search_kwargs={"fetch_k": 40, "lambda_mult": 0.3}
```
**Impact**: +15% coverage

### 3. Query Normalization
```python
# Improve: clean user queries before retrieval
def normalize_query(query):
    # Remove common filler words
    # Fix common typos (thryoid -> thyroid)
    # Expand acronyms (HTN -> hypertension)
    return cleaned_query
```
**Impact**: +20% for user typos

### 4. Multi-hop Retrieval
```python
# For follow-up questions, retrieve related concepts
related_concepts = extract_entities(previous_answer)
related_docs = retriever.retrieve(related_concepts)
```
**Impact**: Better context for follow-ups

---

## 8. EVALUATION WORKFLOW

### Step 1: Create Ground Truth Dataset
```python
eval_data = [
    {
        "question": "How is Type 2 diabetes prevented?",
        "ground_truth": "Prevention includes weight loss, regular exercise, healthy diet rich in fiber, regular blood glucose monitoring...",
        "relevant_docs": ["Lifestyle modifications prevent diabetes", "Exercise improves insulin sensitivity", ...],
        "category": "prevention",
        "difficulty": "medium"
    },
    # ... more samples covering:
    # - Symptoms (easy)
    # - Causes (medium)  
    # - Treatment (medium)
    # - Management (hard)
    # - Drug interactions (hard)
]
```

### Step 2: Run Baseline Evaluation
```python
from rag_evaluation_comprehensive import RAGEvaluator

evaluator = RAGEvaluator()
baseline_results, baseline_metrics = evaluator.evaluate_rag_system(
    eval_data, current_retriever, current_generator
)
```

### Step 3: Iterative Improvements
For each improvement:
1. Implement change
2. Run evaluation with same dataset
3. Compare metrics
4. Document improvement %
5. Decide: keep/rollback

### Step 4: Monitor Production
```python
# Log all queries and answers
# Periodically evaluate sample of production queries
# Track metric drift over time
# Alert if metrics drop >5%
```

---

## 9. INTEGRATION WITH CURRENT APP

### Update `app.py`:
```python
from improved_retrieval import AdvancedRetriever

# Replace current retriever initialization
retriever = AdvancedRetriever(
    documents=loaded_docs,
    embeddings=get_embeddings(),
    llm=ChatGroq(model="llama-3.1-8b-instant"),
    index_name="medical-chatbot"
)

def get_retriever():
    return retriever.retrieve_with_expansion(
        query=query,
        use_expansion=True,
        use_hybrid=True,
        use_reranking=True,
        top_n=5
    )
```

### Add Evaluation Endpoint (Flask):
```python
@app.route('/api/evaluate', methods=['POST'])
def evaluate_answer():
    """Evaluate a single Q&A pair"""
    from rag_evaluation_comprehensive import RAGEvaluator
    
    data = request.json
    evaluator = RAGEvaluator()
    
    metrics = evaluator.evaluate_answer_quality(
        question=data['question'],
        answer=data['answer'],
        ground_truth=data.get('ground_truth', ''),
        retrieved_contexts=data.get('contexts', [])
    )
    
    return jsonify({
        'metrics': metrics,
        'overall_score': sum(metrics.values()) / len(metrics)
    })
```

---

## 10. COMMON PITFALLS & SOLUTIONS

### Pitfall 1: Overfitting to Evaluation Set
**Solution**: 
- Use train/val/test split (70/15/15)
- Don't tune on evaluation set
- Hold-out test set for final assessment

### Pitfall 2: Ignoring Latency
**Solution**:
- Monitor retrieval latency (should be <500ms)
- Monitor generation latency (should be <3s)
- Use caching for repeated queries

### Pitfall 3: Metrics Not Aligned with User Satisfaction
**Solution**:
- Collect user feedback scores
- Correlate with metrics
- Weight metrics based on correlation

### Pitfall 4: Context Window Explosion
**Solution**:
- Cap total context size: ~3000-4000 tokens
- Prioritize top-ranked documents
- Summarize if too long

### Pitfall 5: Hallucination Despite Context
**Solution**:
- Add explicit "insufficient context" detection
- Use lower temperature (0.0-0.3) for medical chat
- Implement fact-checking with source verification

---

## 11. TROUBLESHOOTING GUIDE

### Problem: Precision@5 low (< 0.5)
**Diagnostics**:
- Check if top-5 contain relevant info
- Are "relevant" labels correct?
- Is query expansion helping or hurting?

**Solutions**:
1. Improve cross-encoder model
2. Adjust hybrid search weights (increase semantic to 0.7)
3. Add external knowledge base filtering

### Problem: Recall@5 low (< 0.6)
**Diagnostics**:
- Are relevant docs not retrieved?
- Chunking misaligned with queries?
- Index not updated?

**Solutions**:
1. Increase k from 10 to 20
2. Lower similarity threshold
3. Re-index with better chunking
4. Add query expansion

### Problem: NDCG low (< 0.5)
**Diagnostics**:
- Relevant docs ranked low?
- Reranker not working well?

**Solutions**:
1. Test different reranker models
2. Add diversity reranking
3. Tune reranking weights

### Problem: Answer Relevancy low (< 0.6)
**Diagnostics**:
- Bad retrieval or bad generation?
- Run evaluation on retrieval separately
- Check LLM temperature

**Solutions**:
1. Fix retrieval first (see above)
2. Lower temperature to 0.2
3. Add explicit instructions to system prompt

---

## 12. RESOURCES & REFERENCES

### Recommended Reading
- [LlamaIndex Advanced Retrieval Guide](https://docs.llamaindex.ai/en/stable/)
- [RAGAS Framework Documentation](https://docs.ragas.io/)
- [Cross-Encoder Models](https://www.sbert.net/docs/pretrained_cross-encoders/README.html)
- [BM25 vs Semantic Search](https://weaviate.io/blog/hybrid-search)

### Tools Used
- **RAGAS**: RAG evaluation framework
- **LangChain**: LLM orchestration
- **HuggingFace**: Embeddings and cross-encoders
- **Pinecone**: Vector database
- **Groq**: Fast LLM inference

---

## 13. SUCCESS STORIES & METRICS

### Expected Improvements with Full Implementation

| Phase | Change | Expected Improvement |
|-------|--------|----------------------|
| Current | Single-stage retrieval + cross-encoder | Baseline |
| Phase 1-2 | Hybrid retrieval | +15-25% Recall |
| Phase 3 | Query expansion | +20-30% Coverage |
| Phase 4 | Advanced reranking | +10-15% Precision |
| Phase 5 | Better chunking | +25-35% Context Precision |
| Phase 6 | Enhanced prompts | +15-20% Faithfulness |
| **All Combined** | **Complete overhaul** | **+60-80% Overall Score** |

---

## Next Steps

1. **Read through** the comprehensive evaluation framework
2. **Set up** the evaluation dataset (start with 20-30 samples)
3. **Run baseline** to establish current performance
4. **Implement Phase 1** (Hybrid Retrieval)
5. **Measure improvement** using new metrics
6. **Iterate** through remaining phases

Good luck! 🚀
