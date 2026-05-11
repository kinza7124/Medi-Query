"""
Simple RAG Evaluation Script
=============================
Basic performance evaluation without external evaluation frameworks.
Measures: Response time, context relevance, and basic accuracy indicators.

Author: Kinza
Date: April 29, 2026
"""

import time
import os
from dotenv import load_dotenv
from app import get_rag_chain, get_retriever, rewrite_query_for_retrieval, get_embeddings

load_dotenv()

# Test questions with expected topics
test_cases = [
    {
        "question": "What are the common symptoms of acne?",
        "expected_topic": "acne",
        "expected_keywords": ["pimple", "blackhead", "whitehead", "skin", "oil"]
    },
    {
        "question": "How can abdominal pain be managed?",
        "expected_topic": "abdominal pain",
        "expected_keywords": ["pain", "abdomen", "stomach", "treatment", "medicine"]
    },
    {
        "question": "Is alcohol consumption risky for health?",
        "expected_topic": "alcohol",
        "expected_keywords": ["liver", "disease", "risk", "health", "consumption"]
    },
    {
        "question": "What is diabetes and how to treat it?",
        "expected_topic": "diabetes",
        "expected_keywords": ["blood sugar", "insulin", "glucose", "treatment"]
    },
    {
        "question": "What causes hypertension?",
        "expected_topic": "hypertension",
        "expected_keywords": ["blood pressure", "high", "heart", "causes"]
    }
]

def evaluate_response_time(chain, retriever, test_case):
    """Measure end-to-end response time."""
    start = time.time()
    
    # Query rewrite
    rewrite_start = time.time()
    optimized_query = rewrite_query_for_retrieval(test_case["question"])
    rewrite_time = time.time() - rewrite_start
    
    # Retrieval
    retrieval_start = time.time()
    docs = retriever.invoke(optimized_query)
    retrieval_time = time.time() - retrieval_start
    
    # Generation
    gen_start = time.time()
    response = chain.invoke({
        "input": optimized_query,
        "chat_history": "No previous conversation."
    })
    gen_time = time.time() - gen_start
    
    total_time = time.time() - start
    
    return {
        "rewrite_time": rewrite_time,
        "retrieval_time": retrieval_time,
        "generation_time": gen_time,
        "total_time": total_time,
        "response": response,
        "retrieved_docs": docs
    }

def check_context_relevance(docs, expected_topic):
    """Check if retrieved documents are relevant to expected topic."""
    if not docs:
        return 0.0
    
    relevant_count = 0
    for doc in docs:
        content = doc.page_content.lower()
        if expected_topic.lower() in content:
            relevant_count += 1
    
    return relevant_count / len(docs)

def check_answer_relevance(response, expected_keywords):
    """Check if answer contains expected keywords."""
    response_lower = response.lower()
    matched_keywords = [kw for kw in expected_keywords if kw.lower() in response_lower]
    return len(matched_keywords) / len(expected_keywords) if expected_keywords else 0

def run_evaluation():
    """Run complete evaluation."""
    print("=" * 60)
    print("RAG PIPELINE EVALUATION")
    print("Author: Kinza | Date: April 29, 2026")
    print("=" * 60)
    
    print("\nInitializing models...")
    chain = get_rag_chain()
    retriever = get_retriever()
    print("✓ Models loaded\n")
    
    results = []
    total_rewrite = 0
    total_retrieval = 0
    total_generation = 0
    total_response = 0
    total_context_relevance = 0
    total_answer_relevance = 0
    
    print("Running test cases...")
    print("-" * 60)
    
    for idx, test_case in enumerate(test_cases, 1):
        print(f"\n[{idx}/{len(test_cases)}] {test_case['question']}")
        
        # Evaluate
        metrics = evaluate_response_time(chain, retriever, test_case)
        
        # Check relevance
        context_relevance = check_context_relevance(metrics["retrieved_docs"], test_case["expected_topic"])
        answer_relevance = check_answer_relevance(metrics["response"], test_case["expected_keywords"])
        
        # Print results
        print(f"  ⏱️  Response Time: {metrics['total_time']:.2f}s")
        print(f"     ├─ Query Rewrite: {metrics['rewrite_time']:.2f}s")
        print(f"     ├─ Document Retrieval: {metrics['retrieval_time']:.2f}s")
        print(f"     └─ Answer Generation: {metrics['generation_time']:.2f}s")
        print(f"  📚 Context Relevance: {context_relevance*100:.0f}% ({int(context_relevance*len(metrics['retrieved_docs']))}/{len(metrics['retrieved_docs'])} docs)")
        print(f"  🎯 Answer Relevance: {answer_relevance*100:.0f}% ({int(answer_relevance*len(test_case['expected_keywords']))}/{len(test_case['expected_keywords'])} keywords)")
        print(f"  📝 Retrieved {len(metrics['retrieved_docs'])} documents")
        print(f"  💬 Response preview: {metrics['response'][:100]}...")
        
        # Accumulate
        total_rewrite += metrics['rewrite_time']
        total_retrieval += metrics['retrieval_time']
        total_generation += metrics['generation_time']
        total_response += metrics['total_time']
        total_context_relevance += context_relevance
        total_answer_relevance += answer_relevance
        
        results.append({
            "question": test_case["question"],
            "total_time": metrics['total_time'],
            "context_relevance": context_relevance,
            "answer_relevance": answer_relevance,
            "response": metrics['response']
        })
        
        # Small delay to avoid rate limits
        time.sleep(2)
    
    # Summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    
    n = len(test_cases)
    avg_rewrite = total_rewrite / n
    avg_retrieval = total_retrieval / n
    avg_generation = total_generation / n
    avg_response = total_response / n
    avg_context_rel = (total_context_relevance / n) * 100
    avg_answer_rel = (total_answer_relevance / n) * 100
    
    print(f"\n📊 Average Response Time: {avg_response:.2f}s")
    print(f"   ├─ Query Rewrite: {avg_rewrite:.2f}s")
    print(f"   ├─ Document Retrieval: {avg_retrieval:.2f}s")
    print(f"   └─ Answer Generation: {avg_generation:.2f}s")
    
    print(f"\n📈 Performance Metrics:")
    print(f"   • Average Context Relevance: {avg_context_rel:.0f}%")
    print(f"   • Average Answer Relevance: {avg_answer_rel:.0f}%")
    print(f"   • SLA Compliance (<5s): {'✅ PASS' if avg_response < 5 else '❌ FAIL'}")
    
    print(f"\n✅ Overall RAG Performance: {(avg_context_rel + avg_answer_rel)/2:.0f}%")
    
    # Save results
    import csv
    with open('simple_evaluation_results.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['question', 'total_time', 'context_relevance', 'answer_relevance', 'response'])
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n💾 Results saved to: simple_evaluation_results.csv")
    print("=" * 60)

if __name__ == "__main__":
    try:
        run_evaluation()
    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
