# Medical AI Chatbot - Testing Documentation
<<<<<<< HEAD
**Author:** Kinza  
**Date:** May 11, 2026  
=======

**Author:** Kinza  
**Date:** April 29, 2026  
>>>>>>> 0f3dabdf0489b2ce5e7d2ba60cbccf4a3d92b1ce
**Version:** 1.0

## Table of Contents
1. [Test Plan Overview](#1-test-plan-overview)
<<<<<<< HEAD
2. [Test Suite Structure](#2-test-suite-structure)
3. [Unit Tests](#3-unit-tests)
4. [Smoke Tests](#4-smoke-tests)
5. [Regression Tests](#5-regression-tests)
6. [Functional Tests](#6-functional-tests)
7. [Integration Tests](#7-integration-tests)
8. [Security Tests](#8-security-tests)
9. [Performance Tests](#9-performance-tests)
10. [Test Execution](#10-test-execution)
11. [Test Results Summary](#11-test-results-summary)
=======
2. [Unit Tests](#2-unit-tests)
3. [Integration Tests](#3-integration-tests)
4. [Functional Tests](#4-functional-tests)
5. [Regression Tests](#5-regression-tests)
6. [Performance Tests](#6-performance-tests)
7. [Security Tests](#7-security-tests)
8. [Test Execution Results](#8-test-execution-results)
>>>>>>> 0f3dabdf0489b2ce5e7d2ba60cbccf4a3d92b1ce

---

## 1. Test Plan Overview

### 1.1 Objectives
- Verify all functional requirements are met
- Validate system performance under expected load
- Ensure security measures are effective
- Confirm regression-free operation after changes

### 1.2 Scope
<<<<<<< HEAD
- **In Scope**: Query processing, RAG pipeline, UI functionality, API integration, security
=======
- **In Scope**: Query processing, RAG pipeline, UI functionality, API integration
>>>>>>> 0f3dabdf0489b2ce5e7d2ba60cbccf4a3d92b1ce
- **Out of Scope**: External API internal workings (Groq, Pinecone infrastructure)

### 1.3 Test Environment
```
Hardware: Windows 10/11, 8GB RAM, Intel i5/i7
<<<<<<< HEAD
Software: Python 3.11+, Chrome/Firefox browser
=======
Software: Python 3.9+, Chrome/Firefox browser
>>>>>>> 0f3dabdf0489b2ce5e7d2ba60cbccf4a3d92b1ce
Network: Stable internet (10+ Mbps)
APIs: Groq API key, Pinecone API key
```

---

<<<<<<< HEAD
## 2. Test Suite Structure

The test suite is organized in the `tests/` directory:

| File | Description | Test Count |
|------|-------------|------------|
| `test_app.py` | Original unit tests | 20 |
| `test_smoke.py` | Quick sanity checks | 17 |
| `test_regression.py` | Regression tests | 24 |
| `test_functional.py` | End-to-end functional tests | 23 |
| `test_integration.py` | Full pipeline integration tests | 18 |
| `test_security.py` | Security vulnerability tests | 28 |
| `test_performance.py` | Performance and load tests | 17 |

---

## 3. Unit Tests

### 3.1 Query Processing Tests
```python
test_sanitize_input_basic()       # Input sanitization
test_greeting_detection()         # Greeting detection
test_get_greeting_response_identity()  # Bot identity response
test_get_greeting_response_hello()     # Hello response
test_get_greeting_response_medical_query()  # Medical queries
```

### 3.2 Conversation Memory Tests
```python
test_format_chat_history_empty()         # Empty history
test_format_chat_history_with_messages() # History formatting
test_format_chat_history_limit()         # History limit (6 messages)
```

### 3.3 Response Processing Tests
```python
test_clean_answer_text_meta_phrases()    # Remove meta phrases
test_extract_subject_from_question()     # Extract question subject
test_needs_clinical_safety_note()        # Safety note detection
test_append_clinical_safety_note()       # Append disclaimer
```

### 3.4 Query Rewrite Tests
```python
test_rewrite_query_for_retrieval_success()  # Query rewrite
test_rewrite_query_greeting_passthrough()   # Greeting passthrough
test_rewrite_query_empty_input()            # Empty input handling
=======
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
>>>>>>> 0f3dabdf0489b2ce5e7d2ba60cbccf4a3d92b1ce
```

---

<<<<<<< HEAD
## 4. Smoke Tests

Quick sanity checks for basic functionality:

### 4.1 Flask App Tests
- `test_index_route_returns_200` - Index page loads
- `test_index_contains_title` - Title present
- `test_clear_route_exists` - Clear endpoint works
- `test_get_route_exists` - Chat endpoint works

### 4.2 Helper Function Tests
- `test_token_counter_import` - Token counter imports
- `test_token_counter_count` - Token counting works
- `test_token_counter_fits` - Token budget checking
- `test_clean_text_function` - Text cleaning
- `test_is_boilerplate_detection` - Boilerplate detection
- `test_content_classification` - Content type classification

### 4.3 Session Management Tests
- `test_session_creation` - Session initialization
- `test_session_cleared_on_clear` - Clear functionality

### 4.4 Configuration Tests
- `test_max_history_messages_config` - History limit (20)
- `test_enable_extractor_flag` - Extractor flag exists
- `test_intent_section_map_defined` - Intent mapping defined
=======
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
>>>>>>> 0f3dabdf0489b2ce5e7d2ba60cbccf4a3d92b1ce

---

## 5. Regression Tests

<<<<<<< HEAD
Ensures existing functionality remains working after code changes:

### 5.1 Query Processing Regression
- All greetings detected correctly
- Medical queries not flagged as greetings
- Greeting responses work
- Medical queries return None

### 5.2 Chat History Regression
- Empty history shows default message
- Single exchange formatting works
- Last 3 exchanges included
- Role labeling correct

### 5.3 Answer Processing Regression
- Meta-phrases removed from answers
- Subject extraction works
- Safety notes added for medical queries
- Bullet point formatting for lists

### 5.4 Query Rewrite Regression
- Greetings pass through unchanged
- Empty input handled properly
- Chain called for medical queries

### 5.5 Metadata Filtering Regression
- Symptom queries get filter
- Cause queries get filter
- Treatment queries get filter
- Generic queries handled

### 5.6 Request Logs Regression
- Logs can be created
- Entries can be added
- Can retrieve all logs
- Can clear logs

---

## 6. Functional Tests

End-to-end user scenarios:

### 6.1 Chat Flow Tests
- `test_ft001_basic_medical_query` - Basic query
- `test_ft002_pronoun_resolution_single_topic` - Pronoun resolution
- `test_ft003_pronoun_resolution_topic_switch` - Topic switch
- `test_ft005_non_medical_identity_query` - Identity query
- `test_ft010_empty_input_handling` - Empty input

### 6.2 UI Interaction Tests
- Index page loads with all elements
- Clear button functionality works
- Multiple conversation turns work

### 6.3 Query Processing Tests
- Medical terms preserved in rewrite
- Intent detection for symptoms
- Intent detection for causes
- Intent detection for treatment

### 6.4 Response Processing Tests
- Clinical safety note for medications
- Clinical safety note for symptoms
- Answer formatting for list questions

### 6.5 Session Management Tests
- Session initialized on first request
- Chat history accumulates
- Chat history capped at limit

---

## 7. Integration Tests

### 7.1 Full Pipeline Tests
- Chat flow returns 200
- JSON structure returned
- Session persists across requests
- Clear session works
- Empty message handling

### 7.2 RAG Chain Tests
- Chain formats context correctly
- Document retrieval returns formatted string

### 7.3 UI Integration Tests
- Index page loads
- Required elements present
- CSS file accessible

### 7.4 Error Handling Tests
- Invalid route returns 404
- Large message handling
- Special characters handled

---

## 8. Security Tests

### 8.1 XSS Prevention Tests
- Script tag handling
- Img onerror handling
- JavaScript URI handling
- Iframe injection prevention
- Nested payloads
- HTML entity encoding

### 8.2 SQL Injection Prevention Tests
- Tautology attacks handled
- UNION attacks handled
- Destructive queries handled
- Comment attacks handled

### 8.3 Input Validation Tests
- Empty input handling
- Whitespace-only input
- Extremely long input
- Unicode input
- Binary data input
- Special characters

### 8.4 Session Security Tests
- Cookie flags (in testing mode)
- Session not persistent
- Session cleared properly

### 8.5 API Key Security Tests
- No API keys in HTML
- No API keys in JavaScript
- Missing keys handling

### 8.6 Response Security Tests
- No internal paths exposed
- No internal hostnames
- Safe error messages

### 8.7 Data Privacy Tests
- No PII in logs
- Chat history not persisted
- Session data limited (20 messages)

---

## 9. Performance Tests

### 9.1 Response Time Tests
- Simple query response time < 10s
- Page load time < 3s
- Clear endpoint < 1s

### 9.2 Helper Function Performance
- Token counter speed (1000 ops < 1s)
- Token fits check speed
- Text cleaning speed
- Boilerplate detection speed
- Content classification speed

### 9.3 Memory Usage Tests
- Token counter singleton
- Session history limit (20)

### 9.4 Concurrency Tests
- Concurrent requests handled
- Concurrent session access

### 9.5 Caching Tests
- Embeddings cached
- LLM cached
- RAG chain cached

---

## 10. Test Execution

### 10.1 Running All Tests
```bash
# Using pytest directly
python -m pytest tests/ -v

# Using the test runner
python run_tests.py
```

### 10.2 Running Specific Test Categories
```bash
# Smoke tests (fast)
python run_tests.py smoke

# Regression tests
python run_tests.py regression

# Functional tests
python run_tests.py functional

# Integration tests
python run_tests.py integration

# Security tests
python run_tests.py security

# Performance tests
python run_tests.py performance
```

### 10.3 Running with Coverage
```bash
python run_tests.py --coverage
```

### 10.4 Running Specific Test File
```bash
python -m pytest tests/test_app.py -v
python -m pytest tests/test_smoke.py -v
python -m pytest tests/test_regression.py -v
=======
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
>>>>>>> 0f3dabdf0489b2ce5e7d2ba60cbccf4a3d92b1ce
```

---

<<<<<<< HEAD
## 11. Test Results Summary

### Latest Test Run
```
Test Run Date: May 11, 2026
Tester: Automated
Version: 1.0

SUMMARY:
Total Tests:  61 (core tests)
Passed:       59
Failed:       0
Skipped:      2
Pass Rate:    96.7%

CRITICAL ISSUES:
- [ ] None

NOTES:
- 2 tests skipped (require live API keys)
- All core functionality tested
- Security tests created but require manual execution
- Performance tests created with proper timeouts
```

### Test Categories Status

| Category | Status | Notes |
|----------|--------|-------|
| Unit Tests | ✅ PASS | 18/20 (2 skipped) |
| Smoke Tests | ✅ PASS | 17/17 |
| Regression Tests | ✅ PASS | 24/24 |
| Functional Tests | ⚠️ PARTIAL | Requires API for full run |
| Integration Tests | ⚠️ PARTIAL | Requires API for full run |
| Security Tests | ✅ CREATED | Manual execution recommended |
| Performance Tests | ✅ CREATED | Some require API |

### Recommendations
- ✅ Ready for core deployment
- ⚠️ Security tests should be run manually before production
- ⚠️ Performance benchmarks should be run with live API
- ✅ Regression tests should be run before each release
=======
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
>>>>>>> 0f3dabdf0489b2ce5e7d2ba60cbccf4a3d92b1ce

---

## Appendices

<<<<<<< HEAD
### A. Test Runner Usage
```bash
# Run all tests
python run_tests.py

# Run with verbose output
python run_tests.py -v

# Run with coverage
python run_tests.py --coverage

# Run specific test type
python run_tests.py smoke -v

# Run tests matching keyword
python run_tests.py -k "test_name"

# Run only failed tests from last run
python run_tests.py --lf
```

### B. Required Dependencies
```
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.12.0
requests>=2.31.0
```

### C. CI/CD Integration
Add to your CI pipeline:
```bash
# Run tests on every commit
python -m pytest tests/test_app.py tests/test_smoke.py tests/test_regression.py -v --tb=short
```

---

**End of Testing Documentation**
=======
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
>>>>>>> 0f3dabdf0489b2ce5e7d2ba60cbccf4a3d92b1ce
