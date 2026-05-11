"""
Comprehensive RAG Evaluation Framework
======================================
This module provides a complete evaluation pipeline for RAG systems with:
- Precision@K, Recall@K metrics
- NDCG, MRR (Mean Reciprocal Rank), MAP (Mean Average Precision)
- F1-Score, Accuracy, BLEU, ROUGE
- Ragas metrics (Faithfulness, Answer Relevancy, Context Precision/Recall)
- Detailed per-query analysis and aggregated results
"""

import os
import time
import logging
import json
import math
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import f1_score, accuracy_score, classification_report

from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

# RAGAS imports
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

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class EvaluationMetrics:
    """Container for evaluation results"""
    question: str
    answer: str
    ground_truth: str
    retrieved_docs: List[str]
    
    # Rank-based metrics
    precision_at_1: float = 0.0
    precision_at_3: float = 0.0
    precision_at_5: float = 0.0
    precision_at_10: float = 0.0
    recall_at_3: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    
    # Ranking metrics
    mrr: float = 0.0  # Mean Reciprocal Rank
    ndcg_at_5: float = 0.0  # Normalized Discounted Cumulative Gain
    map_at_5: float = 0.0  # Mean Average Precision
    
    # Answer quality metrics
    answer_relevancy_score: float = 0.0
    faithfulness_score: float = 0.0
    context_precision_score: float = 0.0
    context_recall_score: float = 0.0
    
    # Text similarity metrics
    exact_match: int = 0  # 1 if answer matches ground truth exactly
    semantic_similarity: float = 0.0  # Cosine similarity
    bleu_score: float = 0.0
    rouge_l_score: float = 0.0
    
    # Aggregate
    overall_score: float = 0.0


class RAGEvaluator:
    """Comprehensive RAG evaluation system"""
    
    def __init__(
        self,
        embeddings_model: HuggingFaceEmbeddings = None,
        use_ragas: bool = True,
        ragas_model: str = None,
        retrieval_similarity_threshold: float = 0.55,
        rate_limit_timeout_seconds: int = 120,
        rate_limit_initial_wait: int = 5,
        rate_limit_max_wait: int = 60,
    ):
        """Initialize evaluator with embeddings model"""
        self.embeddings = embeddings_model or HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.use_ragas = use_ragas
        self.retrieval_similarity_threshold = retrieval_similarity_threshold
        self.groq_llm = None
        if self.use_ragas:
            self.groq_llm = ChatGroq(
                model=ragas_model or os.getenv("GROQ_EVAL_MODEL", "llama-3.1-8b-instant"),
                temperature=0.1,
                groq_api_key=os.getenv("GROQ_EVAL_API_KEY"),
            )
        self.rate_limit_timeout_seconds = rate_limit_timeout_seconds
        self.rate_limit_initial_wait = rate_limit_initial_wait
        self.rate_limit_max_wait = rate_limit_max_wait

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            cast = float(value)
            if math.isnan(cast) or math.isinf(cast):
                return default
            return cast
        except (TypeError, ValueError):
            return default

    def _is_relevant_doc(self, retrieved_doc: str, relevant_docs: List[str]) -> bool:
        """Mark a retrieved doc relevant if it semantically matches any ground-truth relevant doc."""
        if not retrieved_doc or not relevant_docs:
            return False

        max_similarity = max(
            (self._semantic_similarity(retrieved_doc, rel_doc) for rel_doc in relevant_docs),
            default=0.0,
        )
        return max_similarity >= self.retrieval_similarity_threshold
        
    @staticmethod
    def _is_rate_limit_error(error: Exception) -> bool:
        message = str(error).lower()
        return "rate limit" in message or "429" in message or "rate_limit" in message

    def _handle_rate_limit(self, retry_after: float, deadline: float):
        """Handle rate limit with a hard timeout budget."""
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                f"Rate limit retry budget exceeded after {self.rate_limit_timeout_seconds} seconds"
            )

        sleep_for = min(retry_after, remaining)
        logger.warning(
            f"Rate limit reached. Retrying after {sleep_for:.1f} seconds (remaining budget {remaining:.1f}s)..."
        )
        time.sleep(sleep_for)

    def evaluate_retrieval(
        self,
        query: str,
        retrieved_docs: List[str],
        relevant_docs: List[str],
        k_values: List[int] = [1, 3, 5, 10]
    ) -> Dict[str, float]:
        """
        Evaluate retrieval quality using rank-based metrics
        
        Args:
            query: Original query string
            retrieved_docs: List of retrieved document snippets (in order)
            relevant_docs: List of relevant document snippets (ground truth)
            k_values: K values for evaluation (e.g., [1, 3, 5, 10])
            
        Returns:
            Dictionary of metrics
        """
        metrics = {}
        # Retrieval metrics are embedding-based and do not call provider APIs.
        # Keep this path deterministic and independent from LLM quota issues.
        for k in [1, 3, 5, 10]:
            top_k_docs = retrieved_docs[:k]
            if not top_k_docs:
                metrics[f'precision_at_{k}'] = 0.0
                continue

            relevant_in_top_k = sum(
                1 for doc in top_k_docs if self._is_relevant_doc(doc, relevant_docs)
            )
            metrics[f'precision_at_{k}'] = relevant_in_top_k / float(len(top_k_docs))

        for k in [3, 5, 10]:
            top_k_docs = retrieved_docs[:k]
            if not top_k_docs or not relevant_docs:
                metrics[f'recall_at_{k}'] = 0.0
                continue

            relevant_in_top_k = sum(
                1 for doc in top_k_docs if self._is_relevant_doc(doc, relevant_docs)
            )
            metrics[f'recall_at_{k}'] = relevant_in_top_k / float(len(relevant_docs))

        metrics['mrr'] = self._compute_mrr(retrieved_docs, relevant_docs)
        metrics['ndcg_at_5'] = self._compute_ndcg(retrieved_docs[:5], relevant_docs)
        metrics['map_at_5'] = self._compute_map(retrieved_docs[:5], relevant_docs)

        return metrics
    
    def evaluate_answer_quality(
        self,
        question: str,
        answer: str,
        ground_truth: str,
        retrieved_contexts: List[str],
        use_ragas: bool = True
    ) -> Dict[str, float]:
        """
        Evaluate answer quality using text similarity and RAGAS metrics
        
        Args:
            question: Original question
            answer: Generated answer
            ground_truth: Ground truth answer
            retrieved_contexts: Retrieved context docs
            use_ragas: Whether to use RAGAS metrics
            
        Returns:
            Dictionary of quality metrics
        """
        metrics = {}
        
        # Text similarity metrics
        metrics['semantic_similarity'] = self._semantic_similarity(
            answer, ground_truth
        )
        metrics['exact_match'] = int(
            self._normalize_text(answer) == self._normalize_text(ground_truth)
        )
        metrics['bleu_score'] = self._compute_bleu(answer, ground_truth)
        metrics['rouge_l_score'] = self._compute_rouge_l(answer, ground_truth)
        
        # RAGAS metrics
        if use_ragas and self.use_ragas:
            ragas_scores = self._compute_ragas_metrics(
                question, answer, ground_truth, retrieved_contexts
            )
            metrics.update(ragas_scores)
        else:
            metrics.update({
                'faithfulness_score': 0.0,
                'answer_relevancy_score': 0.0,
                'context_precision_score': 0.0,
                'context_recall_score': 0.0,
            })
        
        return metrics
    
    def _semantic_similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts"""
        try:
            emb1 = self.embeddings.embed_query(text1)
            emb2 = self.embeddings.embed_query(text2)
            similarity = cosine_similarity([emb1], [emb2])[0][0]
            return float(similarity)
        except Exception as e:
            logger.error(f"Error computing semantic similarity: {e}")
            return 0.0
    
    def _compute_mrr(
        self,
        retrieved_docs: List[str],
        relevant_docs: List[str]
    ) -> float:
        """Compute Mean Reciprocal Rank"""
        for rank, doc in enumerate(retrieved_docs, 1):
            is_relevant = self._is_relevant_doc(doc, relevant_docs)
            if is_relevant:
                return 1.0 / rank
        return 0.0
    
    def _compute_ndcg(
        self,
        retrieved_docs: List[str],
        relevant_docs: List[str],
        k: int = 5
    ) -> float:
        """Compute NDCG at K"""
        if not relevant_docs:
            return 0.0
        
        # Compute DCG
        dcg = 0.0
        for rank, doc in enumerate(retrieved_docs[:k], 1):
            relevance = 1.0 if self._is_relevant_doc(doc, relevant_docs) else 0.0
            dcg += relevance / np.log2(rank + 1)
        
        # Compute IDCG (ideal DCG)
        idcg = sum(
            1.0 / np.log2(rank + 1) for rank in range(1, min(k, len(relevant_docs)) + 1)
        )
        
        return dcg / idcg if idcg > 0 else 0.0
    
    def _compute_map(
        self,
        retrieved_docs: List[str],
        relevant_docs: List[str],
        k: int = 5
    ) -> float:
        """Compute Mean Average Precision at K"""
        if not relevant_docs:
            return 0.0
        
        precisions = []
        num_relevant = 0
        
        for rank, doc in enumerate(retrieved_docs[:k], 1):
            is_relevant = self._is_relevant_doc(doc, relevant_docs)
            if is_relevant:
                num_relevant += 1
                precisions.append(num_relevant / rank)
        
        return sum(precisions) / min(k, len(relevant_docs)) if precisions else 0.0
    
    def _compute_bleu(self, generated: str, reference: str) -> float:
        """Compute BLEU score (simplified 1-gram version)"""
        try:
            from nltk.translate.bleu_score import sentence_bleu
            from nltk.tokenize import word_tokenize
            
            reference_tokens = word_tokenize(reference.lower())
            generated_tokens = word_tokenize(generated.lower())
            
            score = sentence_bleu(
                [reference_tokens],
                generated_tokens,
                weights=(1,)  # 1-gram
            )
            return float(score)
        except Exception as e:
            logger.warning(f"BLEU computation failed: {e}")
            return 0.0
    
    def _compute_rouge_l(self, generated: str, reference: str) -> float:
        """Compute ROUGE-L score (LCS-based)"""
        try:
            from rouge_score import rouge_scorer
            scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
            scores = scorer.score(reference, generated)
            return float(scores['rougeL'].fmeasure)
        except Exception as e:
            logger.warning(f"ROUGE-L computation failed: {e}")
            return 0.0
    
    def _compute_ragas_metrics(
        self,
        question: str,
        answer: str,
        ground_truth: str,
        contexts: List[str]
    ) -> Dict[str, float]:
        """Compute RAGAS metrics"""
        if not self.use_ragas or self.groq_llm is None:
            return {
                'faithfulness_score': 0.0,
                'answer_relevancy_score': 0.0,
                'context_precision_score': 0.0,
                'context_recall_score': 0.0,
            }

        try:
            data_dict = {
                "question": [question],
                "answer": [answer],
                "contexts": [[ctx for ctx in contexts]],
                "ground_truth": [ground_truth],
            }
            
            dataset = Dataset.from_dict(data_dict)
            
            eval_llm = LangchainLLMWrapper(self.groq_llm)
            eval_embeddings = LangchainEmbeddingsWrapper(self.embeddings)
            
            run_config = RunConfig(
                max_workers=1,
                max_retries=3,
                timeout=min(60, self.rate_limit_timeout_seconds),
            )
            
            scores = evaluate(
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
            
            result_dict = scores.to_pandas().to_dict('records')[0]
            return {
                'faithfulness_score': self._safe_float(result_dict.get('faithfulness', 0.0), default=0.0),
                'answer_relevancy_score': self._safe_float(result_dict.get('answer_relevancy', 0.0), default=0.0),
                'context_precision_score': self._safe_float(result_dict.get('context_precision', 0.0), default=0.0),
                'context_recall_score': self._safe_float(result_dict.get('context_recall', 0.0), default=0.0),
            }
        except Exception as e:
            logger.warning(f"RAGAS metrics computation failed: {e}")
            return {
                'faithfulness_score': 0.0,
                'answer_relevancy_score': 0.0,
                'context_precision_score': 0.0,
                'context_recall_score': 0.0,
            }
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for comparison"""
        import re
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = ' '.join(text.split())
        return text
    
    def evaluate_rag_system(
        self,
        eval_dataset: List[Dict[str, Any]],
        retrieval_func,
        generation_func,
        output_file: str = "rag_comprehensive_evaluation.csv",
        use_ragas: bool = None,
    ) -> Tuple[List[EvaluationMetrics], Dict[str, float]]:
        """
        Complete RAG system evaluation
        
        Args:
            eval_dataset: List of dicts with 'question', 'ground_truth', 'relevant_docs'
            retrieval_func: Function to retrieve docs for a query
            generation_func: Function to generate answer from query + context
            output_file: CSV file to save results
            
        Returns:
            Tuple of (list of per-query metrics, aggregated metrics)
        """
        all_results = []
        metric_aggregates = defaultdict(list)
        
        logger.info(f"Starting evaluation on {len(eval_dataset)} samples...")
        
        for idx, item in enumerate(eval_dataset):
            try:
                question = item['question']
                ground_truth = item['ground_truth']
                relevant_docs = item.get('relevant_docs', [ground_truth])
                
                logger.info(f"[{idx+1}/{len(eval_dataset)}] Processing: {question[:50]}...")
                
                # Retrieve documents
                retrieved_docs = retrieval_func(question)
                retrieved_texts = [doc.page_content if isinstance(doc, Document) else str(doc) 
                                  for doc in retrieved_docs]
                
                # Generate answer
                answer = generation_func(question, retrieved_texts)
                
                # Evaluate retrieval
                retrieval_metrics = self.evaluate_retrieval(
                    question, retrieved_texts, relevant_docs
                )
                
                # Evaluate answer
                answer_metrics = self.evaluate_answer_quality(
                    question, answer, ground_truth, retrieved_texts,
                    use_ragas=self.use_ragas if use_ragas is None else use_ragas,
                )
                
                # Combine metrics
                eval_result = EvaluationMetrics(
                    question=question,
                    answer=answer,
                    ground_truth=ground_truth,
                    retrieved_docs=retrieved_texts,
                    **retrieval_metrics,
                    **answer_metrics
                )
                
                # Compute overall score (weighted average)
                eval_result.overall_score = self._compute_overall_score(
                    retrieval_metrics, answer_metrics
                )
                
                all_results.append(eval_result)
                
                # Aggregate
                for metric_name, metric_value in asdict(eval_result).items():
                    if isinstance(metric_value, (int, float)):
                        metric_aggregates[metric_name].append(self._safe_float(metric_value, default=0.0))
                
                # Rate limit handling
                if idx < len(eval_dataset) - 1:
                    time.sleep(5)
                    
            except Exception as e:
                logger.error(f"Error evaluating sample {idx}: {e}")
                continue
        
        # Compute aggregate statistics
        aggregate_stats = {}
        for metric_name, values in metric_aggregates.items():
            if values:
                arr = np.asarray(values, dtype=float)
                aggregate_stats[f'{metric_name}_mean'] = float(np.nanmean(arr)) if not np.all(np.isnan(arr)) else 0.0
                aggregate_stats[f'{metric_name}_std'] = float(np.nanstd(arr)) if not np.all(np.isnan(arr)) else 0.0
                aggregate_stats[f'{metric_name}_min'] = float(np.nanmin(arr)) if not np.all(np.isnan(arr)) else 0.0
                aggregate_stats[f'{metric_name}_max'] = float(np.nanmax(arr)) if not np.all(np.isnan(arr)) else 0.0
        
        # Save results
        self._save_results(all_results, aggregate_stats, output_file)
        
        return all_results, aggregate_stats
    
    @staticmethod
    def _compute_overall_score(
        retrieval_metrics: Dict[str, float],
        answer_metrics: Dict[str, float]
    ) -> float:
        """Compute weighted overall score"""
        # Weight components: retrieval (40%), answer quality (60%)
        retrieval_score = np.mean([
            retrieval_metrics.get('precision_at_5', 0),
            retrieval_metrics.get('recall_at_5', 0),
            retrieval_metrics.get('ndcg_at_5', 0),
        ])
        
        answer_score = np.nanmean([
            answer_metrics.get('answer_relevancy_score', 0),
            answer_metrics.get('faithfulness_score', 0),
            answer_metrics.get('semantic_similarity', 0),
        ])

        if np.isnan(answer_score):
            answer_score = answer_metrics.get('semantic_similarity', 0)
        
        return 0.4 * retrieval_score + 0.6 * answer_score
    
    @staticmethod
    def _save_results(
        results: List[EvaluationMetrics],
        aggregates: Dict[str, float],
        output_file: str
    ) -> None:
        """Save evaluation results to CSV and JSON"""
        # Convert to DataFrame
        results_dict = [asdict(r) for r in results]
        df = pd.DataFrame(results_dict)
        
        # Save CSV
        csv_file = output_file
        df.to_csv(csv_file, index=False)
        logger.info(f"Detailed results saved to {csv_file}")
        
        # Save JSON summary
        json_file = output_file.replace('.csv', '_summary.json')
        with open(json_file, 'w') as f:
            json.dump(aggregates, f, indent=2)
        logger.info(f"Summary saved to {json_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("RAG EVALUATION SUMMARY")
        print("="*60)
        for metric, value in sorted(aggregates.items()):
            if '_mean' in metric:
                print(f"{metric:<40} {value:.4f}")
        print("="*60 + "\n")


# Example evaluation dataset (can be expanded)
SAMPLE_EVAL_DATASET = [
    {
        "question": "What are the common symptoms of acne?",
        "ground_truth": "Common symptoms of acne include blackheads, whiteheads, pimples, pustules, nodules, oily skin, and potential scarring.",
        "relevant_docs": [
            "Acne symptoms include blackheads and whiteheads",
            "Acne presents with pimples and oily skin",
        ]
    },
    {
        "question": "How is diabetes managed?",
        "ground_truth": "Diabetes management includes blood sugar monitoring, medication (insulin or oral drugs), dietary changes, exercise, and regular medical checkups.",
        "relevant_docs": [
            "Diabetes requires monitoring blood glucose levels",
            "Treatment includes insulin and oral medications",
            "Lifestyle changes like diet and exercise are important",
        ]
    },
    {
        "question": "What causes hypertension?",
        "ground_truth": "Hypertension causes include genetics, high sodium diet, obesity, stress, alcohol consumption, and sedentary lifestyle.",
        "relevant_docs": [
            "Genetic factors contribute to hypertension",
            "Dietary salt intake affects blood pressure",
            "Obesity is a risk factor for high blood pressure",
        ]
    },
]


if __name__ == "__main__":
    # This would be implemented by the user with their actual RAG functions
    logger.info("Comprehensive RAG Evaluator ready for use")
    logger.info("Import RAGEvaluator and use evaluate_rag_system() method")
