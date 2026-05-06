# Medical AI Chatbot - Testing Documentation

**Author:** Kinza  
**Date:** April 29, 2026  
**Version:** 1.0

## Table of Contents
1. [Test Plan Overview](#1-test-plan-overview)
2. [Unit Tests](#2-unit-tests)
3. [Integration Tests](#3-integration-tests)
4. [Functional Tests](#4-functional-tests)
5. [Regression Tests](#5-regression-tests)
6. [Performance Tests](#6-performance-tests)
7. [Security Tests](#7-security-tests)
8. [Test Execution Results](#8-test-execution-results)

---

## 1. Test Plan Overview

### 1.1 Objectives
- Verify all functional requirements are met
- Validate system performance under expected load
- Ensure security measures are effective
- Confirm regression-free operation after changes

### 1.2 Scope
- **In Scope**: Query processing, RAG pipeline, UI functionality, API integration
- **Out of Scope**: External API internal workings (Groq, Pinecone infrastructure)

### 1.3 Test Environment
```
Hardware: Windows 10/11, 8GB RAM, Intel i5/i7
Software: Python 3.9+, Chrome/Firefox browser
Network: Stable internet (10+ Mbps)
APIs: Groq API key, Pinecone API key
```

---

## 2. Unit Tests

### 2.1 Query Processing Functions

#### Test: Greeting Detection and Input Routing
```python
def test_is_greeting_or_personal_question():
    """Test greeting and personal question detection."""
    test_cases = [
        "hello",
        "hi there",
        "who are you",
        "what is your name",
    ]
    for query in test_cases:
        assert is_greeting_or_personal_question(query) is True
```

#### Test: Greeting Detection
```python
def test_is_greeting_or_personal_question():
    """Test greeting and personal question detection."""
    greetings = ["hello", "hi there", "who are you", "how are you"]
    medical = ["what is diabetes", "symptoms of flu"]
    
    for q in greetings:
        assert is_greeting_or_personal_question(q) == True
    for q in medical:
        assert is_greeting_or_personal_question(q) == False
```

#### Test: Chat History Formatting
```python
def test_format_chat_history():
    """Test history formatting for prompt injection."""
    history = [
        {"role": "user", "content": "what is acne"},
        {"role": "assistant", "content": "Acne is..."},
    ]
    formatted = format_chat_history(history)
    assert "User: what is acne" in formatted
    assert "Assistant: Acne is" in formatted
```

### 2.2 Document Processing Functions

#### Test: Context Formatting
```python
def test_format_docs():
    """Test document concatenation for context."""
    from langchain_core.documents import Document
    docs = [
        Document(page_content="Diabetes is a disease."),
        Document(page_content="It affects blood sugar."),
    ]
    result = format_docs(docs)
    assert "Diabetes is a disease.\n\nIt affects blood sugar." == result
```

### 2.3 Response Cleaning Functions

#### Test: Answer Text Cleaning
```python
def test_clean_answer_text():
    """Test removal of meta-references."""
    test_cases = [
        ("Based on the context, diabetes is...", "diabetes is..."),
        ("According to the provided context...", ""),
    ]
    for input_text, expected in test_cases:
        result = clean_answer_text("what is diabetes", input_text)
        # Check meta-phrases removed
        assert "Based on the context" not in result
```

#### Test: Clinical Safety Note
```python
def test_append_clinical_safety_note():
    """Test safety note addition for medical queries."""
    answer = "Take aspirin for headache."
    query = "how to treat headache"
    result = append_clinical_safety_note(query, answer)
    assert "consult a doctor" in result.lower() or "physician" in result.lower()
```

---

## 3. Integration Tests

### 3.1 API Integration

#### Test: Groq API Connection
```python
import pytest

def test_groq_api_connectivity():
    """Verify Groq API is accessible."""
    from langchain_groq import ChatGroq
    
    llm = ChatGroq(model="llama-3.3-70b-versatile")
    response = llm.invoke("Say 'test passed'")
    assert "test passed" in response.content.lower()
```

#### Test: Pinecone Vector Search
```python
def test_pinecone_retrieval():
    """Verify vector database returns results."""
    from src.helper import download_hugging_face_embeddings
    from langchain_pinecone import PineconeVectorStore
    
    embeddings = download_hugging_face_embeddings()
    docsearch = PineconeVectorStore.from_existing_index(
        index_name="medical-chatbot",
        embedding=embeddings
    )
    
    results = docsearch.similarity_search("diabetes", k=3)
    assert len(results) > 0
    assert all(hasattr(doc, 'page_content') for doc in results)
```

### 3.2 RAG Pipeline Integration

#### Test: End-to-End RAG Chain
```python
def test_rag_pipeline_end_to_end():
    """Test full RAG pipeline execution."""
    from app import get_rag_chain
    
    chain = get_rag_chain()
    result = chain.invoke({
        "input": "what is diabetes",
        "chat_history": "No previous conversation."
    })
    
    assert result is not None
    assert len(result) > 0
    assert "diabetes" in result.lower()
```

---

## 4. Functional Tests

### 4.1 Test Execution Log

| Test ID | Test Scenario | Steps | Expected Result | Actual Result | Status |
|---------|---------------|-------|-----------------|---------------|--------|
| FT-001 | Basic medical query | 1. Open chat 2. Type "what is diabetes" 3. Submit | Response about diabetes within 5s | [To be filled] | [ ] |
| FT-002 | Pronoun resolution - single topic | 1. Ask "what is acne" 2. Ask "how to treat it" | Response about acne treatment | [To be filled] | [ ] |
| FT-003 | Pronoun resolution - topic switch | 1. Ask "what is drowsiness" 2. Ask "what is acne" 3. Ask "how to treat it" | Response about acne treatment (most recent) | [To be filled] | [ ] |
| FT-004 | Context abstention | 1. Ask "what is quantum physics" | Response stating info not available | [To be filled] | [ ] |
| FT-005 | Non-medical query | 1. Ask "who are you" | Bot introduction response | [To be filled] | [ ] |
| FT-006 | Emergency detection | 1. Ask "I'm having chest pain" | Emergency guidance included | [To be filled] | [ ] |
| FT-007 | Clear chat | 1. Have conversation 2. Click clear 3. Ask pronoun query | Pronoun not resolved / graceful handling | [To be filled] | [ ] |
| FT-008 | Typo correction | 1. Ask "what is diabts" | Query rewritten to "diabetes" | [To be filled] | [ ] |
| FT-009 | Multi-turn conversation | 1. Ask "what is hypertension" 2. Ask "what are its symptoms" 3. Ask "how to prevent it" | All responses contextually linked to hypertension | [To be filled] | [ ] |
| FT-010 | Empty input | 1. Submit empty message | Error message or no action | [To be filled] | [ ] |

### 4.2 Detailed Test Procedure

#### FT-002: Pronoun Resolution Test
**Objective**: Verify system resolves pronouns using most recent topic

**Steps**:
1. Navigate to chat interface
2. Enter: "what is acne"
3. Wait for response
4. Enter: "how to treat it"
5. Wait for response

**Expected**:
- First response: Information about acne
- Second response: Information about acne treatment (not general or unrelated)
- Console log shows: `Original: 'how to treat it' -> Rewritten: 'treatment for acne'`

**Validation**:
- [ ] Response contains "acne" or "pimple" or related terms
- [ ] Response does not discuss unrelated conditions
- [ ] Query rewrite logged correctly

#### FT-003: Topic Switch Pronoun Resolution
**Objective**: Verify pronouns resolve to most recent topic after topic switch

**Steps**:
1. Clear chat history
2. Ask: "what is drowsiness"
3. Ask: "what is acne"  
4. Ask: "how to treat it"

**Expected**:
- Response addresses acne treatment (not drowsiness treatment)

**Validation**:
- [ ] Response mentions acne, pimples, or skin treatment
- [ ] Response does NOT mention sleep, drowsiness, or fatigue

---

## 5. Regression Tests

### 5.1 Regression Test Suite

| ID | Change Category | Test Focus | Pass Criteria |
|----|-----------------|------------|---------------|
| RT-001 | Prompt changes | Verify all existing queries work | No degradation in response quality |
| RT-002 | Dependency update | Test with updated library versions | All imports successful |
| RT-003 | Model change | Test with different LLM model | Responses generated correctly |
| RT-004 | UI modification | Cross-browser compatibility | UI renders correctly on Chrome/Firefox |
| RT-005 | API key rotation | Test with new credentials | System operational after key change |
| RT-006 | Database reindexing | Test after vector DB update | Retrieval still functional |

### 5.2 Regression Execution Checklist

```
Before Release Checklist:
□ All unit tests pass
□ All integration tests pass
□ Functional test suite executed
□ No critical bugs open
□ Performance metrics within SLA
□ Security scan completed
□ Documentation updated
```

---

## 6. Performance Tests

### 6.1 Response Time Benchmarks

| Operation | Target | Acceptable | Measured |
|-----------|--------|------------|----------|
| Query Rewrite | < 1s | < 2s | [ ] |
| Document Retrieval | < 2s | < 3s | [ ] |
| LLM Generation | < 3s | < 5s | [ ] |
| End-to-End | < 5s | < 8s | [ ] |
| Model Preloading | < 30s | < 60s | [ ] |
| Page Load | < 3s | < 5s | [ ] |

### 6.2 Load Testing

#### Test: Concurrent User Simulation
```python
import concurrent.futures
import time

def test_concurrent_users():
    """Test system with 10 concurrent users."""
    queries = ["what is diabetes"] * 10
    
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(send_query, queries))
    end = time.time()
    
    assert all(r.status_code == 200 for r in results)
    assert (end - start) < 30  # All 10 queries within 30s
```

### 6.3 Resource Utilization

| Resource | Baseline | Under Load | Peak |
|----------|----------|------------|------|
| CPU Usage | 5-10% | 40-60% | < 80% |
| Memory | 500MB | 1GB | < 2GB |
| API Calls/min | 0 | 60 | < 100 |

---

## 7. Security Tests

### 7.1 Input Validation Tests

#### Test: XSS Prevention
```python
def test_xss_prevention():
    """Verify XSS attempts are neutralized."""
    xss_attempts = [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert('xss')>",
        "javascript:alert('xss')",
    ]
    
    for attempt in xss_attempts:
        response = send_query(attempt)
        # Response should not contain executable script
        assert "<script>" not in response.text
```

#### Test: SQL Injection Prevention
```python
def test_sql_injection():
    """Verify SQL injection attempts fail."""
    sql_attempts = [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "UNION SELECT * FROM passwords",
    ]
    
    for attempt in sql_attempts:
        response = send_query(attempt)
        # Should not crash or expose data
        assert response.status_code == 200
```

### 7.2 API Security Tests

| Test ID | Test Case | Method | Expected |
|---------|-----------|--------|----------|
| SC-001 | Missing API key | Remove GROQ_API_KEY | Graceful error handling |
| SC-002 | Invalid API key | Use fake key | Error message, no crash |
| SC-003 | Key exposure check | View page source | No API keys visible |
| SC-004 | Session security | Inspect cookies | Secure, HttpOnly flags |

---

## 8. Test Execution Results

### 8.1 Test Summary Template

```
Test Run Date: [YYYY-MM-DD]
Tester: [Name]
Version: [Commit Hash/Version]

SUMMARY:
Total Tests: XX
Passed: XX
Failed: XX
Skipped: XX
Pass Rate: XX%

CRITICAL ISSUES:
- [ ] None
- [ ] Issue 1: [Description]

RECOMMENDATIONS:
- 

APPROVAL:
[ ] Ready for deployment
[ ] Requires fixes
```

### 8.2 Defect Log Template

| ID | Date | Severity | Description | Steps to Reproduce | Expected | Actual | Status |
|----|------|----------|-------------|-------------------|----------|--------|--------|
| D-001 | | High | | | | | Open/Closed |

---

## Appendices

### A. Test Data

**Sample Medical Queries**:
- "what is diabetes mellitus"
- "symptoms of type 2 diabetes"
- "causes of hypertension"
- "how to treat migraine"
- "what is acne and how to prevent it"

**Sample Non-Medical Queries**:
- "who are you"
- "hello"
- "what time is it"
- "what is 2+2"

### B. Tools Used

- **Unit Testing**: pytest
- **API Testing**: Postman / curl
- **Load Testing**: locust / Apache JMeter
- **Security Testing**: OWASP ZAP (optional)
- **Browser Testing**: Chrome DevTools, Firefox Inspector

### C. Test Automation

```bash
# Run the project test suite
pytest tests/test_app.py -v

# Run system workflow tests (route/session/cache behavior)
pytest tests/test_system_workflows.py -v

# Run with concise output
pytest -q tests/test_app.py

# Run all tests
pytest -q

# Run the evaluation script in quota-safe mode
EVAL_USE_RAGAS=false EVAL_SAMPLE_SIZE=5 EVAL_GENERATION_MODEL=llama-3.1-8b-instant python run_comprehensive_evaluation.py
```

### 8.3 Current Automated Test Snapshot

Latest validation performed during report preparation:

- `pytest -q tests/test_app.py tests/test_system_workflows.py` now reports **27 passed, 2 skipped**.
- `tests/test_app.py` now also includes input validation (`500` char cap, script-like payload rejection) and emergency keyword detection coverage.
- `tests/test_system_workflows.py` adds route-level system workflow checks for `/health`, `/clear`, `/get`, and `/response-status`.
- The app exports `format_docs` and accepts string-based chat history in `rewrite_query_for_retrieval`.
- Quota-safe evaluation mode is available for report generation when Groq limits are exhausted.

---

**End of Testing Documentation**
