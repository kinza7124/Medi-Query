# Medical AI Chatbot - Testing Documentation

**Author:** Kinza  
**Date:** May 13, 2026  
**Version:** 1.1

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
10. [Refactored & System Tests](#10-refactored--system-tests)
11. [Test Execution](#11-test-execution)
12. [Test Results Summary](#12-test-results-summary)

---

## 1. Test Plan Overview

### 1.1 Objectives
- Verify all functional requirements are met
- Validate system performance under expected load
- Ensure security measures against XSS and SQLi
- Confirm regression-free operation after environmental stabilization

### 1.2 Scope
- **In Scope**: Query processing, RAG pipeline, UI functionality, API integration, security, session management, and LLM rotation logic.
- **Out of Scope**: Internal infrastructure of external providers (Groq, Pinecone).

### 1.3 Test Environment
```
Hardware: Windows 10/11, 8GB+ RAM
Software: Python 3.11+, Flask 2.x
Environment: Isolated mocking layer for LangChain/Pydantic stability
```

---

## 2. Test Suite Structure

The test suite is comprehensive, covering unit to system-level verification:

| File | Category | Description |
|------|----------|-------------|
| `test_app.py` | Unit | Core application logic and helpers |
| `test_smoke.py` | Smoke | Rapid sanity checks for main endpoints |
| `test_regression.py` | Regression | Verifies fixes for historical bugs |
| `test_functional.py` | Functional | End-to-end user conversation scenarios |
| `test_integration.py` | Integration | Component-to-component communication |
| `test_security.py` | Security | Vulnerability and input validation tests |
| `test_performance.py` | Performance | Latency and concurrency benchmarks |
| `test_medical_chatbot_refactored.py` | Refactored | Environment-stable core logic tests |
| `test_system_workflows.py` | System | Multi-step cross-functional workflows |

---

## 3. Unit Tests (`test_app.py`)

Focuses on individual functions in `app.py`:
- **Query Processing**: Sanitization, greeting detection, and identity responses.
- **Conversation Memory**: History formatting and message limits.
- **Response Processing**: Meta-phrase removal and subject extraction.
- **Safety**: Disclaimer triggers for clinical keywords (headache, pain, etc.).

---

## 4. Smoke Tests (`test_smoke.py`)

Verified core system health:
- **Connectivity**: Index, health, and clear routes return 200 OK.
- **Logging**: Request logs thread-local storage validation.
- **Configuration**: Constant definitions and environment flags.

---

## 5. Regression Tests (`test_regression.py`)

Ensures past issues stay resolved:
- **Query Expansion**: Verified LLM calls for complex medical queries.
- **Pronoun Resolution**: Deterministic anchoring for "it", "that", etc.
- **Logging**: Correct retrieval and clearing of request logs.
- **Metadata Filtering**: Accurate section targeting in vector searches.

---

## 6. Functional Tests (`test_functional.py`)

End-to-end user scenarios:
- **Topic Switching**: Correct pronoun resolution after switching topics (e.g., drowsiness -> acne).
- **Empty Inputs**: Graceful error handling for blank messages.
- **Emergency Detection**: Recognition of critical symptoms (chest pain, etc.).
- **Formatting**: Bullet-point conversion for list-style answers.

---

## 7. Integration Tests (`test_integration.py`)

Validates the RAG pipeline flow:
- **JSON Structure**: Verifies API responses match the expected frontend schema.
- **Session Persistence**: Chat history maintained across multiple requests.
- **Vector Search**: Context formatting from Pinecone metadata.

---

## 8. Security Tests (`test_security.py`)

Vulnerability protection:
- **XSS**: Neutralization of `<script>`, `onerror`, and `iframe` injections.
- **SQLi**: Protection against tautology and UNION-based attacks.
- **API Security**: Ensures no keys are exposed in HTML or client-side code.
- **Data Privacy**: Prevents PII leak in logs and limits session storage.

---

## 9. Performance Tests (`test_performance.py`)

Efficiency benchmarks:
- **Latency**: Average response time verification.
- **Concurrency**: Handling multiple simultaneous users.
- **Caching**: Validation of singleton preloading for embeddings and LLMs.

---

## 10. Refactored & System Tests

Specialized suites created for environment stability:
- **`test_medical_chatbot_refactored.py`**: Uses pre-import mocking to bypass Pydantic v1/v2 conflicts.
- **`test_system_workflows.py`**: Validates the async `/response-status` cache and health monitoring.

---

## 11. Test Execution

Run the complete suite:
```bash
pytest tests/ -v
```

Run specific categories:
```bash
pytest tests/test_security.py -v
pytest tests/test_medical_chatbot_refactored.py -v
```

---

## 12. Test Results Summary

### Latest Test Run (May 13, 2026)
**Status: ✅ ALL CORE TESTS PASSED**

| Metric | Result |
|--------|--------|
| **Total Tests** | 153 |
| **Passed** | 151 |
| **Skipped** | 2 (Requires Live API) |
| **Failed** | 0 |
| **Pass Rate** | **100% (of active tests)** |

### Critical Fixes Applied:
1. **NameError**: Resolved missing `time` import in `app.py`.
2. **ImportError**: Synchronized tests with actual function names (`validate_user_input`, etc.).
3. **Session Stability**: Fixed session initialization on the landing page.
4. **Intent Detection**: Expanded regex to capture visual symptoms ("what does it look like").
5. **Caching**: Implemented response caching for async status checking.
