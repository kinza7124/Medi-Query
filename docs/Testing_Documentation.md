# Medical AI Chatbot - Testing Documentation
**Author:** Kinza  
**Date:** May 11, 2026  
**Version:** 1.0

## Table of Contents
1. [Test Plan Overview](#1-test-plan-overview)
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

---

## 1. Test Plan Overview

### 1.1 Objectives
- Verify all functional requirements are met
- Validate system performance under expected load
- Ensure security measures are effective
- Confirm regression-free operation after changes

### 1.2 Scope
- **In Scope**: Query processing, RAG pipeline, UI functionality, API integration, security
- **Out of Scope**: External API internal workings (Groq, Pinecone infrastructure)

### 1.3 Test Environment
```
Hardware: Windows 10/11, 8GB RAM, Intel i5/i7
Software: Python 3.11+, Chrome/Firefox browser
Network: Stable internet (10+ Mbps)
APIs: Groq API key, Pinecone API key
```

---

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
```

---

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

---

## 5. Regression Tests

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
```

---

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

---

## Appendices

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