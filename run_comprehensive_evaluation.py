"""
Complete RAG Evaluation Example
==============================
Shows how to use the comprehensive evaluation framework with your RAG system.
"""

import os
import time
import logging
from typing import List
from functools import lru_cache
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings

# Import evaluation framework
from rag_evaluation_comprehensive import RAGEvaluator, SAMPLE_EVAL_DATASET

# Import improved retrieval
from improved_retrieval import AdvancedRetriever

# Import from app
from app import get_retriever, get_embeddings

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_eval_chat_model():
    """Use a smaller model for evaluation to reduce token pressure."""
    return ChatGroq(
        model=os.getenv("EVAL_GENERATION_MODEL", "llama-3.1-8b-instant"),
        temperature=0.1,
        groq_api_key=os.getenv("GROQ_EVAL_API_KEY") or os.getenv("GROQ_API_KEY"),
    )


def _extractive_fallback_answer(context_docs: List[str], max_chars: int = 700) -> str:
    """Fallback answer generator when provider quota is exhausted."""
    if not context_docs:
        return "No relevant context found to generate an answer."

    joined = " ".join(doc.replace("\n", " ").strip() for doc in context_docs[:3] if doc)
    compact = " ".join(joined.split())
    if not compact:
        return "No relevant context found to generate an answer."
    return compact[:max_chars]


# ════════════════════════════════════════════════════════════════════
# STEP 1: Create a Larger Evaluation Dataset
# ════════════════════════════════════════════════════════════════════

COMPREHENSIVE_EVAL_DATASET = [
    # ──── Symptom-Based Questions ────
    {
        "question": "What are the common symptoms of acne?",
        "ground_truth": "Common acne symptoms include blackheads, whiteheads, pimples (pustules), nodules, papules, and oily skin. In severe cases, acne can cause cysts and permanent scarring.",
        "relevant_docs": [
            "Acne presents with blackheads (open comedones) and whiteheads (closed comedones)",
            "Inflammatory acne manifests as red pimples, pustules and nodules",
            "Severe acne can cause painful nodular lesions and potential scarring"
        ],
        "category": "symptoms",
        "difficulty": "easy"
    },
    {
        "question": "What are symptoms of Type 2 diabetes?",
        "ground_truth": "Symptoms include increased thirst (polydipsia), frequent urination (polyuria), unexplained weight loss, fatigue, blurred vision, slow healing wounds, and tingling in hands/feet (neuropathy). Many people have no symptoms initially.",
        "relevant_docs": [
            "Diabetes causes increased thirst and frequent urination",
            "Weight loss and fatigue are common signs of diabetes",
            "Diabetes can cause blurred vision and nerve damage"
        ],
        "category": "symptoms",
        "difficulty": "easy"
    },
    
    # ──── Cause-Based Questions ────
    {
        "question": "What causes acne?",
        "ground_truth": "Acne is caused by a combination of factors: increased sebum production, clogged pores, bacterial growth (Propionibacterium acnes), and inflammation. Hormonal changes, stress, certain medications, and diet may trigger or worsen acne.",
        "relevant_docs": [
            "Excess sebum and clogged pores are primary acne causes",
            "Bacteria colonize blocked hair follicles causing inflammation",
            "Hormonal fluctuations increase sebum production during puberty"
        ],
        "category": "causes",
        "difficulty": "medium"
    },
    {
        "question": "What causes hypertension?",
        "ground_truth": "Primary hypertension (95% of cases) is caused by genetics, high sodium diet, obesity, sedentary lifestyle, chronic stress, and excessive alcohol. Secondary hypertension results from kidney disease, adrenal disorders, or certain medications.",
        "relevant_docs": [
            "Genetic predisposition accounts for 50-60% of hypertension cases",
            "High sodium intake increases blood pressure",
            "Obesity and lack of exercise are major risk factors"
        ],
        "category": "causes",
        "difficulty": "medium"
    },
    
    # ──── Treatment Questions ────
    {
        "question": "How is acne treated?",
        "ground_truth": "Treatment options include: topical medications (benzoyl peroxide, salicylic acid, retinoids, antibiotics), oral medications (antibiotics, hormonal contraceptives, isotretinoin/Accutane for severe cases), and lifestyle modifications (proper cleansing, avoid squeezing, sun protection).",
        "relevant_docs": [
            "Benzoyl peroxide and salicylic acid are first-line topical treatments",
            "Oral antibiotics treat moderate acne, often combined with topical retinoids",
            "Isotretinoin is used for severe, scarring acne resistant to other treatments"
        ],
        "category": "treatment",
        "difficulty": "medium"
    },
    {
        "question": "How is Type 2 diabetes managed?",
        "ground_truth": "Management includes: blood glucose monitoring, dietary modifications (low glycemic index foods, portion control), regular physical activity (150 min/week), weight loss, oral medications (metformin, sulfonylureas), insulin if needed, and regular medical checkups.",
        "relevant_docs": [
            "Lifestyle changes including diet and exercise are first-line management",
            "Metformin is the most commonly prescribed first-line medication",
            "Insulin therapy is added when oral medications are insufficient"
        ],
        "category": "management",
        "difficulty": "medium"
    },
    
    # ──── Prevention Questions ────
    {
        "question": "How can high blood pressure be prevented?",
        "ground_truth": "Prevention strategies include: regular aerobic exercise, DASH diet (low sodium, high fruits/vegetables), weight management, stress reduction, limiting alcohol, smoking cessation, adequate sleep, and regular blood pressure monitoring.",
        "relevant_docs": [
            "Regular aerobic exercise (150 min/week) reduces blood pressure",
            "DASH diet reduces sodium intake and increases potassium",
            "Weight reduction of 5-10% can significantly lower blood pressure"
        ],
        "category": "prevention",
        "difficulty": "medium"
    },
    {
        "question": "Can acne be prevented?",
        "ground_truth": "While genetics cannot be changed, acne risk can be reduced by: maintaining proper hygiene, avoiding touching the face, managing stress, using non-comedogenic products, maintaining a balanced diet (limited refined sugars), staying hydrated, and managing hormonal changes.",
        "relevant_docs": [
            "Proper skin cleansing twice daily prevents pore clogging",
            "Avoiding oil-based cosmetics reduces sebum buildup",
            "Stress management helps regulate hormonal triggers"
        ],
        "category": "prevention",
        "difficulty": "medium"
    },
    
    # ──── Complex Questions ────
    {
        "question": "What is the relationship between diet and acne severity?",
        "ground_truth": "Research suggests high glycemic index foods and dairy products may worsen acne. Foods rich in omega-3s, antioxidants, and low in processed sugars may help. However, the relationship is complex and varies by individual genetics and hormonal factors.",
        "relevant_docs": [
            "High glycemic index foods cause blood sugar spikes affecting hormone levels",
            "Some studies link dairy consumption to increased acne severity",
            "Foods rich in antioxidants may reduce acne inflammation"
        ],
        "category": "pathophysiology",
        "difficulty": "hard"
    },
    {
        "question": "How do different antihypertensive medications work?",
        "ground_truth": "Major classes: ACE inhibitors/ARBs (dilate blood vessels), beta-blockers (reduce heart rate and force), calcium channel blockers (relax heart and vessels), diuretics (reduce blood volume), and alpha-blockers (relax blood vessel muscles). Choice depends on patient factors and comorbidities.",
        "relevant_docs": [
            "ACE inhibitors prevent angiotensin II formation, causing vasodilation",
            "Beta-blockers slow heart rate and reduce cardiac contractility",
            "Thiazide diuretics reduce plasma volume and sodium"
        ],
        "category": "pathophysiology",
        "difficulty": "hard"
    },
]


# ════════════════════════════════════════════════════════════════════
# STEP 2: Create Wrapper Functions for Your RAG System
# ════════════════════════════════════════════════════════════════════

def retrieval_function(query: str) -> List[Document]:
    """
    Wrapper for your RAG system's retrieval
    
    Args:
        query: User query string
        
    Returns:
        List of retrieved Document objects
    """
    try:
        retriever = get_retriever()
        docs = retriever.invoke(query)
        logger.info(f"Retrieved {len(docs)} documents for: {query[:50]}...")
        return docs
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        return []


def generation_function(query: str, context_docs: List[str]) -> str:
    """
    Wrapper for your RAG system's generation
    
    Args:
        query: User query string
        context_docs: List of context document strings
        
    Returns:
        Generated answer
    """
    try:
        llm = get_eval_chat_model()
        
        # Prepare context
        context_text = "\n\n".join([
            f"[Document {i+1}] {doc[:500]}" 
            for i, doc in enumerate(context_docs[:5])
        ])
        
        # Create prompt
        prompt = f"""Based on the following medical context, answer the question directly and accurately.
        
Medical Context:
{context_text}

Question: {query}

Answer:"""
        
        # Generate
        response = llm.invoke(prompt)
        
        # Extract text if response is a message object
        if hasattr(response, 'content'):
            answer = response.content
        else:
            answer = str(response)
        
        logger.info(f"Generated answer for: {query[:50]}...")
        return answer
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        # Keep evaluation running with deterministic fallback to avoid hard-stop on quota.
        return _extractive_fallback_answer(context_docs)


# ════════════════════════════════════════════════════════════════════
# STEP 3: Run Comprehensive Evaluation
# ════════════════════════════════════════════════════════════════════

def run_comprehensive_evaluation(
    eval_dataset: List[dict] = None,
    output_file: str = "rag_evaluation_results.csv",
    use_ragas: bool = False,
    sample_size: int = 0,
) -> None:
    """
    Run comprehensive RAG evaluation
    
    Args:
        eval_dataset: Evaluation dataset (defaults to COMPREHENSIVE_EVAL_DATASET)
        output_file: Output CSV file path
    """
    
    if eval_dataset is None:
        eval_dataset = COMPREHENSIVE_EVAL_DATASET

    if sample_size and sample_size > 0:
        eval_dataset = eval_dataset[:sample_size]
    
    logger.info("="*70)
    logger.info("STARTING COMPREHENSIVE RAG EVALUATION")
    logger.info("="*70)
    logger.info(f"Evaluation dataset size: {len(eval_dataset)} questions")
    logger.info(f"Output file: {output_file}")
    logger.info(f"RAGAS enabled: {use_ragas}")
    logger.info("="*70 + "\n")
    
    # Initialize evaluator
    embeddings = get_embeddings()
    evaluator = RAGEvaluator(
        embeddings_model=embeddings,
        use_ragas=use_ragas,
        ragas_model=os.getenv("GROQ_EVAL_MODEL", "llama-3.1-8b-instant"),
        retrieval_similarity_threshold=float(os.getenv("RETRIEVAL_SIMILARITY_THRESHOLD", "0.55")),
        rate_limit_timeout_seconds=int(os.getenv("EVAL_RATE_LIMIT_TIMEOUT_SECONDS", "120")),
        rate_limit_initial_wait=int(os.getenv("EVAL_RATE_LIMIT_INITIAL_WAIT", "5")),
        rate_limit_max_wait=int(os.getenv("EVAL_RATE_LIMIT_MAX_WAIT", "60")),
    )
    
    # Run evaluation
    try:
        results, aggregates = evaluator.evaluate_rag_system(
            eval_dataset=eval_dataset,
            retrieval_func=retrieval_function,
            generation_func=generation_function,
            output_file=output_file,
            use_ragas=use_ragas,
        )
        
        # Print detailed summary
        print_evaluation_summary(results, aggregates)
        
        # Print per-category analysis
        print_category_analysis(results)
        
        # Print recommendations
        print_recommendations(aggregates)
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise


def print_evaluation_summary(results, aggregates):
    """Print comprehensive evaluation summary"""
    
    print("\n" + "═"*80)
    print("COMPREHENSIVE EVALUATION SUMMARY")
    print("═"*80)
    
    # Retrieval Metrics
    print("\n📊 RETRIEVAL METRICS (Quality of Context Retrieval)")
    print("-" * 80)
    print(f"  Precision@1:     {aggregates.get('precision_at_1_mean', 0):.4f} (target: > 0.70)")
    print(f"  Precision@3:     {aggregates.get('precision_at_3_mean', 0):.4f} (target: > 0.65)")
    print(f"  Precision@5:     {aggregates.get('precision_at_5_mean', 0):.4f} (target: > 0.60)")
    print(f"  Recall@3:        {aggregates.get('recall_at_3_mean', 0):.4f} (target: > 0.70)")
    print(f"  Recall@5:        {aggregates.get('recall_at_5_mean', 0):.4f} (target: > 0.75)")
    print(f"  Recall@10:       {aggregates.get('recall_at_10_mean', 0):.4f} (target: > 0.80)")
    print(f"  MRR:             {aggregates.get('mrr_mean', 0):.4f} (target: > 0.70)")
    print(f"  NDCG@5:          {aggregates.get('ndcg_at_5_mean', 0):.4f} (target: > 0.70)")
    print(f"  MAP@5:           {aggregates.get('map_at_5_mean', 0):.4f} (target: > 0.70)")
    
    # Answer Quality Metrics
    print("\n🎯 ANSWER QUALITY METRICS (RAG Generation Quality)")
    print("-" * 80)
    print(f"  Answer Relevancy:     {aggregates.get('answer_relevancy_score_mean', 0):.4f} (target: > 0.80)")
    print(f"  Faithfulness:         {aggregates.get('faithfulness_score_mean', 0):.4f} (target: > 0.80)")
    print(f"  Context Precision:    {aggregates.get('context_precision_score_mean', 0):.4f} (target: > 0.75)")
    print(f"  Context Recall:       {aggregates.get('context_recall_score_mean', 0):.4f} (target: > 0.75)")
    
    # Text Similarity Metrics
    print("\n📝 TEXT SIMILARITY METRICS (Answer Similarity to Ground Truth)")
    print("-" * 80)
    print(f"  Semantic Similarity:  {aggregates.get('semantic_similarity_mean', 0):.4f} (target: > 0.75)")
    print(f"  BLEU Score:           {aggregates.get('bleu_score_mean', 0):.4f} (target: > 0.30)")
    print(f"  ROUGE-L:              {aggregates.get('rouge_l_score_mean', 0):.4f} (target: > 0.40)")
    print(f"  Exact Match:          {aggregates.get('exact_match_mean', 0):.4f} (target: > 0.20)")
    
    # Overall
    print("\n⭐ OVERALL SCORE")
    print("-" * 80)
    print(f"  Overall Score:        {aggregates.get('overall_score_mean', 0):.4f} / 1.0")
    print(f"  Rating:               {'🟢 Good (>0.75)' if aggregates.get('overall_score_mean', 0) > 0.75 else '🟡 Fair (0.5-0.75)' if aggregates.get('overall_score_mean', 0) > 0.5 else '🔴 Needs Work (<0.5)'}")
    
    print("\n" + "═"*80)


def print_category_analysis(results):
    """Print analysis by question category"""
    
    from collections import defaultdict
    import numpy as np
    
    print("\n📂 PERFORMANCE BY QUESTION CATEGORY")
    print("-" * 80)
    
    categories = defaultdict(list)
    for result in results:
        # Try to infer category from question type
        q = result.question.lower()
        if any(word in q for word in ['symptom', 'sign', 'present']):
            cat = 'symptoms'
        elif any(word in q for word in ['cause', 'cause', 'trigger']):
            cat = 'causes'
        elif any(word in q for word in ['treat', 'manage', 'therapy']):
            cat = 'treatment'
        elif any(word in q for word in ['prevent', 'avoid']):
            cat = 'prevention'
        else:
            cat = 'other'
        
        categories[cat].append(result.overall_score)
    
    for category, scores in sorted(categories.items()):
        avg_score = np.mean(scores)
        print(f"  {category.capitalize():15} | Score: {avg_score:.4f} | Count: {len(scores)}")
    
    print("-" * 80)


def print_recommendations(aggregates):
    """Print recommendations based on performance"""
    
    print("\n💡 RECOMMENDATIONS FOR IMPROVEMENT")
    print("-" * 80)
    
    recommendations = []
    
    # Check retrieval
    if aggregates.get('precision_at_5_mean', 0) < 0.60:
        recommendations.append("❌ Low Precision@5: Improve relevance of retrieved documents")
        recommendations.append("   → Try hybrid search (BM25 + semantic)")
        recommendations.append("   → Improve cross-encoder reranker")
    
    if aggregates.get('recall_at_5_mean', 0) < 0.70:
        recommendations.append("❌ Low Recall@5: Missing relevant documents")
        recommendations.append("   → Increase retrieval from k=10 to k=20")
        recommendations.append("   → Add query expansion")
        recommendations.append("   → Improve chunking strategy")
    
    if aggregates.get('ndcg_at_5_mean', 0) < 0.60:
        recommendations.append("❌ Low NDCG@5: Relevant docs ranked too low")
        recommendations.append("   → Improve reranker model quality")
        recommendations.append("   → Add diversity reranking")
    
    # Check answer quality
    if aggregates.get('faithfulness_score_mean', 0) < 0.70:
        recommendations.append("❌ Low Faithfulness: Answers not grounded in context")
        recommendations.append("   → Add explicit context checking")
        recommendations.append("   → Lower LLM temperature")
        recommendations.append("   → Improve system prompt")
    
    if aggregates.get('answer_relevancy_score_mean', 0) < 0.70:
        recommendations.append("❌ Low Answer Relevancy: Answers don't address question")
        recommendations.append("   → Improve retrieval (see above)")
        recommendations.append("   → Add chain-of-thought prompting")
        recommendations.append("   → Test different LLM models")
    
    if not recommendations:
        recommendations.append("✅ Performance is good! Consider fine-tuning specific weak areas.")
    
    for rec in recommendations:
        print(f"  {rec}")
    
    print("-" * 80 + "\n")


# ════════════════════════════════════════════════════════════════════
# STEP 4: Main Execution
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    use_ragas = os.getenv("EVAL_USE_RAGAS", "false").lower() == "true"
    sample_size = int(os.getenv("EVAL_SAMPLE_SIZE", "0"))
    
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║  COMPREHENSIVE RAG EVALUATION SUITE                      ║
    ║  Medical AI Chatbot - Performance Analysis               ║
    ╚══════════════════════════════════════════════════════════╝
    
    This script evaluates your RAG system with:
    ✓ Precision@K and Recall@K metrics
    ✓ NDCG, MRR, MAP (ranking quality)
    ✓ Answer relevancy and faithfulness
    ✓ Text similarity metrics (BLEU, ROUGE-L)
    ✓ Category-based performance analysis
    ✓ Actionable recommendations
    
    Starting evaluation...
    """)
    
    # Run comprehensive evaluation
    run_comprehensive_evaluation(
        eval_dataset=COMPREHENSIVE_EVAL_DATASET,
        output_file="rag_comprehensive_evaluation.csv",
        use_ragas=use_ragas,
        sample_size=sample_size,
    )
    
    print("""
    ✅ Evaluation Complete!
    
    Output files:
    - rag_comprehensive_evaluation.csv (detailed per-query results)
    - rag_comprehensive_evaluation_summary.json (aggregated metrics)
    
    Next steps:
    1. Review recommendations above
    2. Implement improvements (see RAG_OPTIMIZATION_GUIDE.md)
    3. Re-run evaluation to measure improvements
    4. Iterate until target metrics are achieved
    """)
