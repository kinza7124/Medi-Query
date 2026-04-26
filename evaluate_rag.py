import os
import time
import logging
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

# Load environment variables
load_dotenv()

# ── Rate-limit configuration ────────────────────────────────────────
# Delay (seconds) between processing each evaluation question
DELAY_BETWEEN_QUESTIONS = 15          # keep well below 30 req/min

# Retry / backoff settings passed to Ragas RunConfig
RAGAS_MAX_RETRIES = 15       # Ragas will retry on errors up to this many times
RAGAS_MAX_WAIT = 120         # max seconds between retries
RAGAS_TIMEOUT = 300          # per-request timeout (seconds)

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)


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

        # 1. Simulate the rewriter
        optimized_query = rewrite_query_for_retrieval(item['question'])

        # Small pause between the rewrite call and the chain call
        time.sleep(5)

        # 2. Get the answer from the chain
        response = chain.invoke({
            "input": optimized_query,
            "chat_history": "No previous conversation."
        })

        # Small pause before retrieval
        time.sleep(3)

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
            log.info(
                "Waiting %d s before next question to respect rate limits …",
                DELAY_BETWEEN_QUESTIONS,
            )
            time.sleep(DELAY_BETWEEN_QUESTIONS)

    # Create dataset
    dataset = Dataset.from_dict(results_data)

    # ── Configure Groq as the evaluation LLM for Ragas ──────────────
    from langchain_groq import ChatGroq
    # Use a dedicated API key for evaluation to avoid sharing rate limits
    # with the main app key
    eval_api_key = os.getenv("GROQ_EVAL_API_KEY", os.getenv("GROQ_API_KEY"))
    groq_llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        groq_api_key=eval_api_key,
    )

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

    # Save results
    score.to_pandas().to_csv("rag_evaluation_results.csv", index=False)
    print("\nResults saved to rag_evaluation_results.csv")

if __name__ == "__main__":
    try:
        run_evaluation()
    except Exception as e:
        print(f"Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        print("Note: Ensure you have your GROQ_API_KEY set up as Ragas needs an LLM for evaluation.")
