"""
evaluate_rag.py — MediQuery RAG Evaluation
============================================
Single-file RAGAS + custom metrics evaluation.

Metrics:
  RAGAS (LLM-judged):
    faithfulness, answer_relevancy, context_precision, context_recall

  Custom (deterministic):
    BLEU, ROUGE-L, Token-F1, Semantic Similarity, Precision@5, Recall@5

Rate-limit handling:
  - 60s pause between each question (answer generation)
  - RAGAS uses max_workers=1 + exponential backoff (max_wait=120s)
  - On 429 error: waits 65s then retries automatically

Usage:
    venv\\Scripts\\python.exe evaluate_rag.py
    (or: set TRANSFORMERS_OFFLINE=1 && venv\\Scripts\\python.exe evaluate_rag.py)

Output:
    rag_evaluation_results.csv    — RAGAS per-question scores
    rag_evaluation_summary.json   — All metrics averaged + per-question breakdown
"""

import os, sys, time, json, re, logging
import numpy as np
from dotenv import load_dotenv
from typing import Any, List, Optional

# LangChain/Ragas imports for the Rotating LLM
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_core.callbacks import CallbackManagerForLLMRun

load_dotenv()
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# ── Rotating LLM Helper ───────────────────────────────────────────

class RotatingGroqLLM(BaseChatModel):
    """
    A wrapper around ChatGroq that rotates through multiple API keys on 429 errors.
    Inherits from BaseChatModel to be compatible with LangChain's Runnable interface.
    """
    api_keys: List[str]
    model_name: str
    temperature: float = 0.0
    current_idx: int = 0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._init_llm()

    def _init_llm(self):
        from langchain_groq import ChatGroq
        # Use object.__setattr__ to bypass Pydantic v1 validation for private attributes
        llm_instance = ChatGroq(
            model=self.model_name,
            temperature=self.temperature,
            groq_api_key=self.api_keys[self.current_idx]
        )
        object.__setattr__(self, '_llm', llm_instance)

    def rotate(self):
        # We must use object.__setattr__ here as well
        new_idx = (self.current_idx + 1) % len(self.api_keys)
        object.__setattr__(self, 'current_idx', new_idx)
        self._init_llm()
        log.info("  ↺ Rate limit hit. Switched to Groq key %d/%d", self.current_idx + 1, len(self.api_keys))

    def _is_rate_limit(self, e) -> bool:
        err = str(e).lower()
        return "429" in err or "rate_limit" in err or "too many requests" in err

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Core method used by LangChain to generate responses."""
        for attempt in range(len(self.api_keys) * 2 + 1):
            try:
                # Access the private _llm via __dict__ or getattr to be safe
                active_llm = getattr(self, '_llm')
                return active_llm._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
            except Exception as e:
                if self._is_rate_limit(e):
                    self.rotate()
                    if self.current_idx == 0:
                        _countdown(65)
                else:
                    raise e
        raise RuntimeError("Max retries exceeded with key rotation.")

    @property
    def _llm_type(self) -> str:
        return "rotating-groq"

    def __getattr__(self, name):
        """Delegate everything else to the current ChatGroq instance."""
        try:
            return super().__getattr__(name)
        except (AttributeError, TypeError):
            active_llm = getattr(self, '_llm', None)
            if active_llm:
                return getattr(active_llm, name)
            raise



# ── Logging ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("evaluation.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────
PAUSE_BETWEEN_QUESTIONS = 65   # seconds — keeps answer-gen well under 30 req/min
RAGAS_MAX_WORKERS       = 1    # serialise all RAGAS LLM calls
RAGAS_MAX_RETRIES       = 20
RAGAS_MAX_WAIT          = 120  # max backoff seconds between retries
RAGAS_TIMEOUT           = 300

# ── Evaluation dataset (5 diverse medical questions) ───────────────
EVAL_DATASET = [
    {
        "question":     "What are the common symptoms of acne?",
        "ground_truth": (
            "Common symptoms of acne include blackheads, whiteheads, pimples, "
            "papules, pustules, nodules, and cysts. The skin may appear oily and "
            "scarring can occur in severe cases."
        ),
    },
    {
        "question":     "What causes type 2 diabetes?",
        "ground_truth": (
            "Type 2 diabetes is caused by insulin resistance and relative insulin "
            "deficiency. Risk factors include obesity, physical inactivity, poor diet, "
            "genetic predisposition, and age."
        ),
    },
    {
        "question":     "How is hypertension treated?",
        "ground_truth": (
            "Hypertension is treated with lifestyle changes such as reduced sodium intake, "
            "regular exercise, and weight loss, as well as medications including ACE "
            "inhibitors, beta-blockers, calcium channel blockers, and diuretics."
        ),
    },
    {
        "question":     "What are the symptoms of asthma?",
        "ground_truth": (
            "Asthma symptoms include wheezing, shortness of breath, chest tightness, "
            "and coughing, especially at night or early morning. Symptoms can be "
            "triggered by allergens, exercise, or cold air."
        ),
    },
    {
        "question":     "How can abdominal pain be managed?",
        "ground_truth": (
            "Abdominal pain management depends on the cause. It may include medications "
            "such as antacids or antispasmodics, dietary changes, rest, and in some "
            "cases surgical intervention."
        ),
    },
]


# ── Custom metric helpers ──────────────────────────────────────────

def _tok(text: str) -> list[str]:
    """Lowercase word tokenisation."""
    return re.findall(r"\b[a-z]+\b", text.lower())


def bleu_score(reference: str, hypothesis: str) -> float:
    """Unigram BLEU with add-1 smoothing and brevity penalty."""
    ref = _tok(reference)
    hyp = _tok(hypothesis)
    if not ref or not hyp:
        return 0.0
    ref_counts: dict[str, int] = {}
    for t in ref:
        ref_counts[t] = ref_counts.get(t, 0) + 1
    clipped = sum(min(hyp.count(t), ref_counts.get(t, 0)) for t in set(hyp))
    precision  = (clipped + 1) / (len(hyp) + 1)
    brevity    = min(1.0, len(hyp) / max(len(ref), 1))
    return round(brevity * precision, 4)


def rouge_l(reference: str, hypothesis: str) -> float:
    """ROUGE-L F1 via longest common subsequence."""
    ref = _tok(reference)
    hyp = _tok(hypothesis)
    if not ref or not hyp:
        return 0.0
    m, n = len(ref), len(hyp)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = dp[i-1][j-1] + 1 if ref[i-1] == hyp[j-1] else max(dp[i-1][j], dp[i][j-1])
    lcs = dp[m][n]
    p = lcs / n if n else 0.0
    r = lcs / m if m else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return round(f, 4)


def token_f1(reference: str, hypothesis: str) -> tuple[float, float, float]:
    """Token-level precision, recall, F1."""
    ref_set = set(_tok(reference))
    hyp_set = set(_tok(hypothesis))
    if not ref_set or not hyp_set:
        return 0.0, 0.0, 0.0
    common = ref_set & hyp_set
    p = len(common) / len(hyp_set)
    r = len(common) / len(ref_set)
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return round(p, 4), round(r, 4), round(f, 4)


def precision_at_k(contexts: list[str], ground_truth: str, k: int = 5) -> float:
    """Fraction of top-K chunks containing ≥3 ground-truth keywords."""
    if not contexts:
        return 0.0
    gt_words = set(_tok(ground_truth))
    hits = sum(
        1 for ctx in contexts[:k]
        if len(set(_tok(ctx)) & gt_words) >= 3
    )
    return round(hits / min(k, len(contexts)), 4)


def recall_at_k(contexts: list[str], ground_truth: str, k: int = 5) -> float:
    """Fraction of ground-truth keywords covered by top-K chunks."""
    if not contexts:
        return 0.0
    gt_words = set(_tok(ground_truth))
    if not gt_words:
        return 0.0
    retrieved: set[str] = set()
    for ctx in contexts[:k]:
        retrieved.update(_tok(ctx))
    return round(len(gt_words & retrieved) / len(gt_words), 4)


def semantic_similarity(answer: str, ground_truth: str, embeddings) -> float:
    """Cosine similarity between answer and ground-truth embeddings."""
    try:
        from sklearn.metrics.pairwise import cosine_similarity as cos_sim
        a = np.array(embeddings.embed_query(answer)).reshape(1, -1)
        g = np.array(embeddings.embed_query(ground_truth)).reshape(1, -1)
        return round(float(cos_sim(a, g)[0][0]), 4)
    except Exception as e:
        log.warning("Semantic similarity failed: %s", e)
        return 0.0


# ── Rate-limit aware invoke ────────────────────────────────────────

def invoke_with_retry(chain, payload: dict, max_retries: int = 5) -> str:
    """Invoke the RAG chain. Key rotation is now handled inside the RotatingGroqLLM."""
    try:
        result = chain.invoke(payload)
        return str(result).strip()
    except Exception as e:
        log.error("Chain invocation failed even with rotation: %s", e)
        raise


def _countdown(seconds: int):
    """Print a live countdown so the user can see progress."""
    for remaining in range(seconds, 0, -5):
        mins, secs = divmod(remaining, 60)
        print(f"\r  ⏳ Waiting {mins:02d}:{secs:02d} for rate limit reset...", end="", flush=True)
        time.sleep(min(5, remaining))
    print("\r  ✓ Resuming...                                    ")


# ── Main ───────────────────────────────────────────────────────────

def run_evaluation():
    log.info("=" * 62)
    log.info("  MediQuery RAG Evaluation — RAGAS + Custom Metrics")
    log.info("  Questions: %d  |  Pause between: %ds", len(EVAL_DATASET), PAUSE_BETWEEN_QUESTIONS)
    log.info("=" * 62)

    # ── Load app components ────────────────────────────────────────
    log.info("Loading app components (models, retriever, chain)...")
    from app import (
        get_rag_chain,
        get_retriever,
        get_embeddings,
        rewrite_query_for_retrieval,
    )
    from langchain_groq import ChatGroq
    from ragas import evaluate as ragas_evaluate
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

    # ── Initialize Rotating LLM ────────────────────────────────────
    groq_key  = os.getenv("GROQ_API_KEY")
    eval_key  = os.getenv("GROQ_EVAL_API_KEY")

    # Use both keys for rotation. Filter out any None values.
    api_keys = [k for k in [groq_key, eval_key] if k]
    if not api_keys:
        log.error("No Groq API keys found in .env (need GROQ_API_KEY and/or GROQ_EVAL_API_KEY)")
        sys.exit(1)

    # Initialize the rotating LLM
    rotating_llm = RotatingGroqLLM(api_keys=api_keys, model_name="llama-3.3-70b-versatile", temperature=0.1)

    # Monkeypatch app.get_llm so the RAG chain uses our rotating LLM
    import app
    app.get_llm = lambda: rotating_llm

    chain      = get_rag_chain()
    retriever  = get_retriever()
    embeddings = get_embeddings()

    # ── Collect answers + contexts ─────────────────────────────────
    log.info("\nPhase 1: Collecting answers and contexts...")
    ragas_data: dict[str, list] = {
        "question": [], "answer": [], "contexts": [], "ground_truth": []
    }
    custom_rows: list[dict] = []

    for idx, item in enumerate(EVAL_DATASET):
        q  = item["question"]
        gt = item["ground_truth"]

        log.info("\n[%d/%d] %s", idx + 1, len(EVAL_DATASET), q)

        # Rewrite
        rewritten = rewrite_query_for_retrieval(q, "No previous conversation.")
        log.info("  → Rewritten: %s", rewritten)

        # Generate answer (with rate-limit retry)
        answer = invoke_with_retry(chain, {
            "input":           q,
            "retrieval_query": rewritten,
            "chat_history":    "No previous conversation.",
        })
        log.info("  → Answer length: %d chars", len(answer))

        # Retrieve contexts
        try:
            docs     = retriever.invoke(rewritten)
            contexts = [doc.page_content for doc in docs]
            log.info("  → Retrieved %d chunks", len(contexts))
        except Exception as e:
            log.error("  Retriever failed: %s", e)
            contexts = []

        # Custom metrics
        bleu   = bleu_score(gt, answer)
        rl     = rouge_l(gt, answer)
        tp, tr, tf = token_f1(gt, answer)
        p5     = precision_at_k(contexts, gt, k=5)
        r5     = recall_at_k(contexts, gt, k=5)
        sem    = semantic_similarity(answer, gt, embeddings)

        log.info(
            "  Custom → BLEU=%.3f  ROUGE-L=%.3f  Token-F1=%.3f  P@5=%.3f  R@5=%.3f  Sem=%.3f",
            bleu, rl, tf, p5, r5, sem,
        )

        ragas_data["question"].append(q)
        ragas_data["answer"].append(answer)
        ragas_data["contexts"].append(contexts)
        ragas_data["ground_truth"].append(gt)

        custom_rows.append({
            "question":            q,
            "bleu":                bleu,
            "rouge_l":             rl,
            "token_precision":     tp,
            "token_recall":        tr,
            "token_f1":            tf,
            "precision_at_5":      p5,
            "recall_at_5":         r5,
            "semantic_similarity": sem,
        })

        # Pause between questions to respect rate limits
        if idx < len(EVAL_DATASET) - 1:
            log.info("  Pausing %ds before next question...", PAUSE_BETWEEN_QUESTIONS)
            _countdown(PAUSE_BETWEEN_QUESTIONS)

    # ── RAGAS evaluation ──────────────────────────────────────────
    log.info("\n" + "=" * 62)
    log.info("Phase 2: RAGAS LLM-judged evaluation (max_workers=1)...")
    log.info("This makes ~%d LLM calls — rate limits handled automatically.", len(EVAL_DATASET) * 4)
    log.info("=" * 62)

    dataset = Dataset.from_dict(ragas_data)

    # Use the same rotating LLM for Phase 2 (RAGAS evaluation)
    eval_llm = LangchainLLMWrapper(rotating_llm)
    eval_emb = LangchainEmbeddingsWrapper(embeddings)

    run_cfg = RunConfig(
        max_workers=RAGAS_MAX_WORKERS,
        max_retries=RAGAS_MAX_RETRIES,
        max_wait=RAGAS_MAX_WAIT,
        timeout=RAGAS_TIMEOUT,
    )

    ragas_scores = ragas_evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=eval_llm,
        embeddings=eval_emb,
        run_config=run_cfg,
    )

    ragas_df = ragas_scores.to_pandas()
    ragas_df.to_csv("rag_evaluation_results.csv", index=False)
    log.info("RAGAS results saved → rag_evaluation_results.csv")

    # ── Compute averages ──────────────────────────────────────────
    ragas_cols = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    ragas_avgs = {
        col: round(float(ragas_df[col].mean()), 4)
        for col in ragas_cols if col in ragas_df.columns
    }

    custom_keys = [
        "bleu", "rouge_l", "token_precision", "token_recall",
        "token_f1", "precision_at_5", "recall_at_5", "semantic_similarity",
    ]
    custom_avgs = {
        k: round(float(np.mean([r[k] for r in custom_rows])), 4)
        for k in custom_keys
    }

    # ── Print results ─────────────────────────────────────────────
    print("\n" + "=" * 62)
    print("  RAGAS METRICS  (LLM-judged, scale 0–1)")
    print("=" * 62)
    labels = {
        "faithfulness":      "Faithfulness       (answer grounded in context?)",
        "answer_relevancy":  "Answer Relevancy   (answers the question?)",
        "context_precision": "Context Precision  (retrieved chunks relevant?)",
        "context_recall":    "Context Recall     (context covers ground truth?)",
    }
    for k, label in labels.items():
        val = ragas_avgs.get(k, "N/A")
        bar = "█" * int(val * 20) if isinstance(val, float) else ""
        print(f"  {label:<50} {val:.4f}  {bar}")

    print("\n" + "=" * 62)
    print("  CUSTOM METRICS  (deterministic, scale 0–1)")
    print("=" * 62)
    custom_labels = {
        "bleu":                "BLEU Score         (n-gram overlap)",
        "rouge_l":             "ROUGE-L            (longest common subsequence F1)",
        "token_precision":     "Token Precision    (answer tokens in ground truth)",
        "token_recall":        "Token Recall       (ground truth tokens in answer)",
        "token_f1":            "Token F1           (harmonic mean of P & R)",
        "precision_at_5":      "Precision@5        (relevant chunks in top-5)",
        "recall_at_5":         "Recall@5           (GT keywords covered by top-5)",
        "semantic_similarity": "Semantic Similarity(cosine via BGE embeddings)",
    }
    for k, label in custom_labels.items():
        val = custom_avgs[k]
        bar = "█" * int(val * 20)
        print(f"  {label:<50} {val:.4f}  {bar}")

    # ── Save summary JSON ─────────────────────────────────────────
    summary = {
        "evaluation_info": {
            "num_questions":  len(EVAL_DATASET),
            "model_answer":   "llama-3.3-70b-versatile",
            "model_rewrite":  "llama-3.1-8b-instant",
            "embeddings":     "BAAI/bge-small-en-v1.5",
            "reranker":       "cross-encoder/ms-marco-MiniLM-L-6-v2",
        },
        "ragas_metrics":  ragas_avgs,
        "custom_metrics": custom_avgs,
        "per_question":   custom_rows,
    }

    with open("rag_evaluation_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 62)
    print("  OUTPUT FILES")
    print("=" * 62)
    print("  rag_evaluation_results.csv    — RAGAS per-question scores")
    print("  rag_evaluation_summary.json   — All metrics + per-question breakdown")
    print("=" * 62)

    return summary


if __name__ == "__main__":
    try:
        run_evaluation()
    except KeyboardInterrupt:
        log.info("\nEvaluation interrupted by user.")
    except Exception as e:
        log.error("Evaluation failed: %s", e)
        import traceback
        traceback.print_exc()
        sys.exit(1)
