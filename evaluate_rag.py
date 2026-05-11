import os
import time
import logging
import re
import numpy as np
from collections import Counter
from dotenv import load_dotenv
from app import get_rag_chain, get_retriever, rewrite_query_for_retrieval, get_embeddings
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.run_config import RunConfig
from datasets import Dataset

# Additional metrics imports
try:
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
    import nltk
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    print("Warning: nltk not available, BLEU score will use simple implementation")

from sklearn.metrics.pairwise import cosine_similarity

# Load environment variables
load_dotenv()

# ── Rate-limit configuration ────────────────────────────────────────
# Delay (seconds) between processing each evaluation question
DELAY_BETWEEN_QUESTIONS = 25          # Increased to stay well below 30 req/min (Groq free tier)

# Retry / backoff settings passed to Ragas RunConfig
RAGAS_MAX_RETRIES = 20       # Ragas will retry on errors up to this many times
RAGAS_MAX_WAIT = 180         # max seconds between retries (3 minutes)
RAGAS_TIMEOUT = 300          # per-request timeout (seconds)

# Groq API Rate Limit Handling
GROQ_RATE_LIMIT_WAIT = 180   # Wait 3 minutes when rate limit hit (daily limit reset)

# Dual API Key Configuration
# GROQ_API_KEY: Primary key for app
# GROQ_EVAL_API_KEY: Secondary key for evaluation (fallback when primary hits rate limit)
PRIMARY_API_KEY = os.getenv("GROQ_API_KEY")
FALLBACK_API_KEY = os.getenv("GROQ_EVAL_API_KEY") or PRIMARY_API_KEY  # Fallback to primary if not set

# Adaptive rate limiting
class AdaptiveRateLimiter:
    """Tracks API calls and adjusts delays to stay within rate limits."""
    def __init__(self, max_requests_per_minute=30, safety_margin=5):
        self.max_requests = max_requests_per_minute - safety_margin  # 25 req/min with margin
        self.call_times = []
        self.current_delay = DELAY_BETWEEN_QUESTIONS
        
    def record_call(self):
        """Record an API call timestamp."""
        now = time.time()
        self.call_times.append(now)
        # Remove calls older than 60 seconds
        self.call_times = [t for t in self.call_times if now - t < 60]
        
    def get_recommended_delay(self):
        """Calculate recommended delay before next call."""
        now = time.time()
        # Clean old calls
        self.call_times = [t for t in self.call_times if now - t < 60]
        
        current_rate = len(self.call_times)
        
        if current_rate >= self.max_requests:
            # We're at the limit, wait until oldest call expires
            if self.call_times:
                wait_time = 60 - (now - self.call_times[0]) + 5  # +5s buffer
                return max(wait_time, 30)
        
        # Adjust delay based on current rate
        if current_rate > self.max_requests * 0.8:
            self.current_delay = min(self.current_delay + 5, 60)
        elif current_rate < self.max_requests * 0.5:
            self.current_delay = max(self.current_delay - 2, 10)
            
        return self.current_delay
    
    def get_status(self):
        """Get current rate limit status."""
        now = time.time()
        self.call_times = [t for t in self.call_times if now - t < 60]
        return {
            "calls_in_last_minute": len(self.call_times),
            "max_allowed": self.max_requests,
            "current_delay": self.current_delay,
            "remaining_capacity": self.max_requests - len(self.call_times)
        }

# Global rate limiter instance
rate_limiter = AdaptiveRateLimiter()

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)


def wait_for_rate_limit_reset(wait_seconds=GROQ_RATE_LIMIT_WAIT):
    """
    Wait for Groq API rate limit to reset.
    Called when 429 errors are encountered.
    """
    log.warning("[WAIT] Groq API rate limit reached. Waiting %d seconds for reset...", wait_seconds)
    log.warning("       Daily token limit: 100,000 | Per-minute request limit: 30")
    
    for remaining in range(wait_seconds, 0, -10):
        mins, secs = divmod(remaining, 60)
        log.info("       Time remaining: %02d:%02d", mins, secs)
        time.sleep(min(10, remaining))
    
    log.info("[OK] Rate limit wait complete. Resuming evaluation...")


def get_groq_llm_with_fallback(primary_key=FALLBACK_API_KEY, fallback_key=PRIMARY_API_KEY):
    """
    Create Groq LLM with primary key, fallback to secondary if rate limited.
    
    WHY SO MANY LLM CALLS?
    - Ragas evaluation requires an LLM to judge answer quality
    - Each metric (faithfulness, relevancy, etc.) needs multiple LLM calls
    - With 3 questions and 4 metrics = ~12+ LLM calls
    - Plus query rewriting and context retrieval = additional calls
    - Total: ~15-20 LLM calls for full evaluation
    """
    try:
        # Try primary key first
        log.info("[LLM] Using primary API key for evaluation...")
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            groq_api_key=primary_key,
        )
        return llm, primary_key
    except Exception as e:
        if "429" in str(e) and fallback_key and fallback_key != primary_key:
            log.info("[LLM] Primary key rate limited, switching to fallback API key...")
            llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                temperature=0,
                groq_api_key=fallback_key,
            )
            return llm, fallback_key
        raise


# ── Custom Evaluation Metrics ─────────────────────────────────────
def calculate_bleu_score(reference, hypothesis):
    """
    Calculate BLEU score between reference (ground truth) and hypothesis (generated answer).
    """
    if NLTK_AVAILABLE:
        # Tokenize into words
        ref_tokens = reference.lower().split()
        hyp_tokens = hypothesis.lower().split()
        
        # Calculate BLEU with smoothing for short sentences
        smoothing = SmoothingFunction().method1
        bleu = sentence_bleu([ref_tokens], hyp_tokens, smoothing_function=smoothing)
        return bleu
    else:
        # Simple fallback using token overlap
        ref_tokens = set(reference.lower().split())
        hyp_tokens = set(hypothesis.lower().split())
        if not ref_tokens:
            return 0.0
        overlap = len(ref_tokens & hyp_tokens)
        return overlap / len(ref_tokens)


def calculate_precision_at_k(retrieved_contexts, relevant_info, k=5):
    """
    Calculate Precision@K - proportion of retrieved documents that are relevant.
    """
    if not retrieved_contexts or k <= 0:
        return 0.0
    
    # Check how many retrieved contexts contain relevant keywords
    relevant_keywords = set(relevant_info.lower().split())
    retrieved_k = retrieved_contexts[:k]
    
    relevant_count = 0
    for ctx in retrieved_k:
        ctx_words = set(ctx.lower().split())
        # If significant word overlap, consider it relevant
        overlap = len(ctx_words & relevant_keywords)
        if overlap >= 3:  # At least 3 keywords match
            relevant_count += 1
    
    return relevant_count / len(retrieved_k) if retrieved_k else 0.0


def calculate_recall_at_k(retrieved_contexts, relevant_info, k=5):
    """
    Calculate Recall@K - proportion of relevant documents that are retrieved.
    """
    if not retrieved_contexts or not relevant_info:
        return 0.0
    
    # Simulate relevant documents by checking coverage of ground truth info
    relevant_keywords = set(relevant_info.lower().split())
    retrieved_k = retrieved_contexts[:k]
    
    # Find how many relevant keywords appear in retrieved contexts
    all_retrieved_words = set()
    for ctx in retrieved_k:
        all_retrieved_words.update(ctx.lower().split())
    
    covered_keywords = len(relevant_keywords & all_retrieved_words)
    total_keywords = len(relevant_keywords)
    
    return covered_keywords / total_keywords if total_keywords > 0 else 0.0


def calculate_f1_score(precision, recall):
    """
    Calculate F1 score from precision and recall.
    """
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)


def calculate_semantic_similarity(answer, ground_truth, embeddings):
    """
    Calculate cosine similarity between answer and ground truth embeddings.
    """
    try:
        answer_embedding = embeddings.embed_query(answer)
        gt_embedding = embeddings.embed_query(ground_truth)
        
        # Reshape for sklearn
        answer_embedding = np.array(answer_embedding).reshape(1, -1)
        gt_embedding = np.array(gt_embedding).reshape(1, -1)
        
        similarity = cosine_similarity(answer_embedding, gt_embedding)[0][0]
        return float(similarity)
    except Exception as e:
        log.warning(f"Could not calculate semantic similarity: {e}")
        return 0.0


def calculate_token_f1(answer, ground_truth):
    """
    Calculate token-level F1 score.
    """
    answer_tokens = set(answer.lower().split())
    gt_tokens = set(ground_truth.lower().split())
    
    if not answer_tokens or not gt_tokens:
        return 0.0
    
    # Calculate overlap
    common_tokens = answer_tokens & gt_tokens
    
    precision = len(common_tokens) / len(answer_tokens)
    recall = len(common_tokens) / len(gt_tokens)
    
    return calculate_f1_score(precision, recall)


def calculate_exact_match(answer, ground_truth):
    """
    Check if answer exactly matches ground truth (case insensitive).
    """
    return 1.0 if answer.lower().strip() == ground_truth.lower().strip() else 0.0


def calculate_rouge_l(answer, ground_truth):
    """
    Simple ROUGE-L (Longest Common Subsequence) calculation.
    """
    answer_tokens = answer.lower().split()
    gt_tokens = ground_truth.lower().split()
    
    if not answer_tokens or not gt_tokens:
        return 0.0
    
    # Find Longest Common Subsequence (LCS)
    m, n = len(answer_tokens), len(gt_tokens)
    lcs_matrix = [[0] * (n + 1) for _ in range(m + 1)]
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if answer_tokens[i-1] == gt_tokens[j-1]:
                lcs_matrix[i][j] = lcs_matrix[i-1][j-1] + 1
            else:
                lcs_matrix[i][j] = max(lcs_matrix[i-1][j], lcs_matrix[i][j-1])
    
    lcs_length = lcs_matrix[m][n]
    
    # ROUGE-L F1
    if lcs_length == 0:
        return 0.0
    
    precision = lcs_length / m if m > 0 else 0.0
    recall = lcs_length / n if n > 0 else 0.0
    
    return calculate_f1_score(precision, recall)


# ── Main evaluation ────────────────────────────────────────────────
def run_evaluation():
    """
    Evaluates the RAG pipeline using a sample set of medical questions.
    Includes delays and retry logic to stay within Groq free-tier rate limits.
    """
    print("Starting RAG Evaluation...")

    # Sample evaluation dataset (Questions and Ground Truths)
    # In a real scenario, you would have a much larger dataset.
    eval_questions = [
        {
            "question": "What are the common symptoms of acne?",
            "ground_truth": "Common symptoms of acne include blackheads, whiteheads, pimples, oily skin, and potential scarring."
        },
        {
            "question": "How can abdominal pain be managed?",
            "ground_truth": "Abdominal pain management depends on the cause but can include medications, dietary changes, and in some cases, surgical intervention."
        },
        {
            "question": "Is alcohol consumption risky for health?",
            "ground_truth": "Yes, alcohol consumption carries various health risks including liver disease, cardiovascular issues, and increased cancer risk."
        }
    ]

    results_data = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": []
    }

    chain = get_rag_chain()
    retriever = get_retriever()
    embeddings = get_embeddings()

    for idx, item in enumerate(eval_questions):
        print(f"\nProcessing ({idx+1}/{len(eval_questions)}): {item['question']}")
        
        # Check rate limit status before each question
        status = rate_limiter.get_status()
        log.info(f"[RATE LIMIT] Calls in last minute: {status['calls_in_last_minute']}/{status['max_allowed']}, Delay: {status['current_delay']}s")

        # 1. Simulate the rewriter
        optimized_query = rewrite_query_for_retrieval(item['question'])
        rate_limiter.record_call()

        # Adaptive delay based on current rate
        adaptive_delay = rate_limiter.get_recommended_delay()
        log.info(f"[RATE LIMIT] Recommended delay: {adaptive_delay}s")
        time.sleep(adaptive_delay)

        # 2. Get the answer from the chain
        try:
            response = chain.invoke({
                "input": optimized_query,
                "chat_history": "No previous conversation."
            })
            rate_limiter.record_call()
        except Exception as e:
            if "429" in str(e):
                log.warning("[RATE LIMIT] Hit rate limit on primary key, waiting...")
                time.sleep(60)
                response = chain.invoke({
                    "input": optimized_query,
                    "chat_history": "No previous conversation."
                })
                rate_limiter.record_call()
            else:
                raise

        # 3. Get the retrieved contexts explicitly for evaluation
        docs = retriever.invoke(optimized_query)
        contexts = [doc.page_content for doc in docs]

        # 4. Compile data for Ragas
        results_data["question"].append(item['question'])
        results_data["answer"].append(str(response))
        results_data["contexts"].append(contexts)
        results_data["ground_truth"].append(item['ground_truth'])

        # Wait before next question to respect rate limits
        if idx < len(eval_questions) - 1:
            wait_time = rate_limiter.get_recommended_delay()
            log.info(
                "Waiting %d s before next question to respect rate limits …",
                wait_time,
            )
            time.sleep(wait_time)

    # Calculate custom metrics for each question
    print("\n--- Calculating Custom Metrics ---")
    custom_metrics = {
        "bleu_score": [],
        "precision_at_3": [],
        "recall_at_3": [],
        "token_f1": [],
        "exact_match": [],
        "rouge_l": [],
        "semantic_similarity": []
    }
    
    for idx, item in enumerate(eval_questions):
        answer = results_data["answer"][idx]
        ground_truth = item["ground_truth"]
        contexts = results_data["contexts"][idx]
        
        # BLEU Score
        bleu = calculate_bleu_score(ground_truth, answer)
        custom_metrics["bleu_score"].append(bleu)
        
        # Precision@3 and Recall@3
        p_at_3 = calculate_precision_at_k(contexts, ground_truth, k=3)
        r_at_3 = calculate_recall_at_k(contexts, ground_truth, k=3)
        custom_metrics["precision_at_3"].append(p_at_3)
        custom_metrics["recall_at_3"].append(r_at_3)
        
        # Token F1
        token_f1 = calculate_token_f1(answer, ground_truth)
        custom_metrics["token_f1"].append(token_f1)
        
        # Exact Match
        em = calculate_exact_match(answer, ground_truth)
        custom_metrics["exact_match"].append(em)
        
        # ROUGE-L
        rouge = calculate_rouge_l(answer, ground_truth)
        custom_metrics["rouge_l"].append(rouge)
        
        # Semantic Similarity (using embeddings)
        sem_sim = calculate_semantic_similarity(answer, ground_truth, embeddings)
        custom_metrics["semantic_similarity"].append(sem_sim)
        
        print(f"\nQuestion {idx+1}: {item['question'][:50]}...")
        print(f"  BLEU Score: {bleu:.4f}")
        print(f"  Precision@3: {p_at_3:.4f}")
        print(f"  Recall@3: {r_at_3:.4f}")
        print(f"  Token F1: {token_f1:.4f}")
        print(f"  Exact Match: {em:.4f}")
        print(f"  ROUGE-L: {rouge:.4f}")
        print(f"  Semantic Similarity: {sem_sim:.4f}")

    # Create dataset
    dataset = Dataset.from_dict(results_data)

    # ── Configure Groq as the evaluation LLM for Ragas ──────────────
    from langchain_groq import ChatGroq
    
    # Use dual API key system with fallback
    groq_llm, active_key = get_groq_llm_with_fallback(PRIMARY_API_KEY, FALLBACK_API_KEY)
    
    # Log which key is being used (mask it for security)
    masked_key = active_key[:10] + "..." if active_key else "NOT SET"
    log.info(f"[EVAL] Using API key: {masked_key}")

    # Wrap with Ragas-compatible wrappers (required by Ragas internals)
    eval_llm = LangchainLLMWrapper(groq_llm)
    eval_embeddings = LangchainEmbeddingsWrapper(embeddings)

    # RunConfig: max_workers=1 serialises all LLM calls so the
    # free-tier rate limit (30 req/min) is not exceeded.
    # max_retries + max_wait handle 429 errors automatically.
    run_config = RunConfig(
        max_workers=1,
        max_retries=RAGAS_MAX_RETRIES,
        max_wait=RAGAS_MAX_WAIT,
        timeout=RAGAS_TIMEOUT,
    )

    # Note: Ragas metrics need an LLM to judge the quality.
    # We are using Groq's high-performance Llama model for this.
    print("\nComputing metrics using Groq and local embeddings...")
    print("(This may take a while due to rate-limit pauses on the free tier)\n")
    score = evaluate(
        dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ],
        llm=eval_llm,
        embeddings=eval_embeddings,
        run_config=run_config,
    )

    print("\n--- Evaluation Results ---")
    print(score)

    # Print Custom Metrics Summary
    print("\n--- Custom Metrics Summary ---")
    print(f"Average BLEU Score: {np.mean(custom_metrics['bleu_score']):.4f}")
    print(f"Average Precision@3: {np.mean(custom_metrics['precision_at_3']):.4f}")
    print(f"Average Recall@3: {np.mean(custom_metrics['recall_at_3']):.4f}")
    print(f"Average Token F1: {np.mean(custom_metrics['token_f1']):.4f}")
    print(f"Average Exact Match: {np.mean(custom_metrics['exact_match']):.4f}")
    print(f"Average ROUGE-L: {np.mean(custom_metrics['rouge_l']):.4f}")
    print(f"Average Semantic Similarity: {np.mean(custom_metrics['semantic_similarity']):.4f}")

    # Save results
    score.to_pandas().to_csv("rag_evaluation_results.csv", index=False)
    
    # Save custom metrics
    import json
    custom_metrics_summary = {
        "per_question": {k: [float(v) for v in vals] for k, vals in custom_metrics.items()},
        "averages": {
            "bleu_score": float(np.mean(custom_metrics['bleu_score'])),
            "precision_at_3": float(np.mean(custom_metrics['precision_at_3'])),
            "recall_at_3": float(np.mean(custom_metrics['recall_at_3'])),
            "token_f1": float(np.mean(custom_metrics['token_f1'])),
            "exact_match": float(np.mean(custom_metrics['exact_match'])),
            "rouge_l": float(np.mean(custom_metrics['rouge_l'])),
            "semantic_similarity": float(np.mean(custom_metrics['semantic_similarity']))
        }
    }
    with open("custom_metrics_results.json", "w") as f:
        json.dump(custom_metrics_summary, f, indent=2)
    
    print("\nResults saved to:")
    print("  - rag_evaluation_results.csv (Ragas metrics)")
    print("  - custom_metrics_results.json (Custom metrics)")

if __name__ == "__main__":
    try:
        run_evaluation()
    except Exception as e:
        error_msg = str(e)
        
        # Check if it's a rate limit error
        if "429" in error_msg or "rate_limit" in error_msg or "Too Many Requests" in error_msg:
            log.error("[ERROR] Groq API Rate Limit Error detected!")
            log.error("   Error: %s", error_msg[:200])
            
            # Extract wait time if available in error message
            import re
            wait_match = re.search(r'try again in (\d+)m(\d+\.?\d*)s', error_msg)
            if wait_match:
                mins = int(wait_match.group(1))
                secs = float(wait_match.group(2))
                total_wait = int(mins * 60 + secs) + 10  # Add buffer
                log.info("   Extracted wait time from error: %d minutes %d seconds", mins, int(secs))
            else:
                total_wait = GROQ_RATE_LIMIT_WAIT
            
            # Wait for rate limit reset
            wait_for_rate_limit_reset(total_wait)
            
            # Retry evaluation
            log.info("[RETRY] Retrying evaluation after rate limit reset...")
            try:
                run_evaluation()
            except Exception as retry_error:
                log.error("[FAILED] Retry failed: %s", retry_error)
                import traceback
                traceback.print_exc()
        else:
            print(f"Evaluation failed: {e}")
            import traceback
            traceback.print_exc()
            print("Note: Ensure you have your GROQ_API_KEY set up as Ragas needs an LLM for evaluation.")
