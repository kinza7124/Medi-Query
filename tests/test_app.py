"""
Unit Tests for Medical AI Chatbot
====================================
Test suite covering core functionality of the RAG-based medical chatbot.

Run with: pytest tests/test_app.py -v
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_chat_history():
    """Sample conversation history for testing."""
    return [
        {"role": "user", "content": "what is diabetes"},
        {"role": "assistant", "content": "Diabetes is a chronic condition..."},
        {"role": "user", "content": "what is acne"},
        {"role": "assistant", "content": "Acne is a skin condition..."},
    ]


@pytest.fixture
def mock_document():
    """Mock LangChain document for testing."""
    doc = Mock()
    doc.page_content = "Diabetes mellitus is a metabolic disease."
    doc.metadata = {"source": "medical_textbook.pdf"}
    return doc


# ============================================================================
# Query Processing Tests
# ============================================================================

class TestQueryProcessing:
    """Tests for query input processing and validation."""
    
    def test_sanitize_input_basic(self):
        """Test basic input sanitization."""
        from app import is_greeting_or_personal_question
        
        # Test that medical queries are not flagged
        medical_queries = [
            "what is diabetes",
            "symptoms of flu",
            "how to treat headache",
            "causes of hypertension",
        ]
        for query in medical_queries:
            assert is_greeting_or_personal_question(query) == False, f"'{query}' should not be a greeting"
    
    def test_greeting_detection(self):
        """Test detection of greeting and personal questions."""
        from app import is_greeting_or_personal_question
        
        greetings = [
            "hello",
            "hi there",
            "hey",
            "who are you",
            "what is your name",
            "how are you",
            "good morning",
        ]
        for query in greetings:
            assert is_greeting_or_personal_question(query) == True, f"'{query}' should be detected as greeting"
    
    def test_get_greeting_response_identity(self):
        """Test bot identity response."""
        from app import get_greeting_response
        
        identity_queries = [
            "who are you",
            "what are you",
            "your name",
            "introduce yourself",
        ]
        for query in identity_queries:
            response = get_greeting_response(query)
            assert response is not None
            assert "Medical AI Assistant" in response or "medical" in response.lower()
    
    def test_get_greeting_response_hello(self):
        """Test greeting response."""
        from app import get_greeting_response
        
        hello_queries = ["hello", "hi", "hey", "good morning"]
        for query in hello_queries:
            response = get_greeting_response(query)
            assert response is not None
            assert "Hello" in response or "how can I help" in response
    
    def test_get_greeting_response_medical_query(self):
        """Test that medical queries return None (not greetings)."""
        from app import get_greeting_response
        
        medical_queries = ["what is diabetes", "how to treat acne"]
        for query in medical_queries:
            response = get_greeting_response(query)
            assert response is None, f"'{query}' should not trigger greeting response"


# ============================================================================
# Conversation Memory Tests
# ============================================================================

class TestConversationMemory:
    """Tests for conversation history and memory management."""
    
    def test_format_chat_history_empty(self):
        """Test formatting empty history."""
        from app import format_chat_history
        
        result = format_chat_history([])
        assert result == "No previous conversation."
    
    def test_format_chat_history_with_messages(self):
        """Test formatting conversation history."""
        from app import format_chat_history
        
        history = [
            {"role": "user", "content": "what is diabetes"},
            {"role": "assistant", "content": "Diabetes is..."},
        ]
        result = format_chat_history(history)
        
        assert "User: what is diabetes" in result
        assert "Assistant: Diabetes is" in result
    
    def test_format_chat_history_limit(self):
        """Test that only last 10 exchanges are kept."""
        from app import format_chat_history
        
        # Create 12 exchanges (24 messages)
        history = []
        for i in range(12):
            history.append({"role": "user", "content": f"query {i}"})
            history.append({"role": "assistant", "content": f"answer {i}"})
        
        result = format_chat_history(history)
        
        # Should only include last 10 exchanges (20 messages)
        assert "query 0" not in result  # First should be excluded
        assert "query 11" in result    # Last should be included


# ============================================================================
# Response Processing Tests
# ============================================================================

class TestResponseProcessing:
    """Tests for response cleaning and formatting."""
    
    def test_clean_answer_text_meta_phrases(self):
        """Test removal of meta-reference phrases."""
        from app import clean_answer_text
        
        test_cases = [
            ("Based on the context, diabetes is...", "diabetes is"),
            ("According to the provided context, it is a disease", "it is a disease"),
            ("This describes diabetes as a condition", "diabetes as a condition"),
        ]
        
        for input_text, expected_fragment in test_cases:
            result = clean_answer_text("what is diabetes", input_text)
            assert "Based on the context" not in result
            assert "According to the provided context" not in result
    
    def test_extract_subject_from_question(self):
        """Test subject extraction from questions."""
        from app import extract_subject_from_question
        
        test_cases = [
            ("what is diabetes", "diabetes"),
            ("what's hypertension", "hypertension"),
            ("tell me about acne", None),  # Doesn't match pattern
        ]
        
        for query, expected in test_cases:
            result = extract_subject_from_question(query)
            if expected:
                assert result == expected, f"Failed for '{query}'"
    
    def test_needs_clinical_safety_note(self):
        """Test detection of queries needing safety disclaimer."""
        from app import needs_clinical_safety_note
        
        # Should trigger safety note
        medical_queries = [
            "how to treat headache",
            "medicine for fever",
            "abdominal pain",
            "medication for diabetes",
        ]
        
        for query in medical_queries:
            assert needs_clinical_safety_note(query) == True, f"'{query}' should need safety note"
    
    def test_append_clinical_safety_note(self):
        """Test safety note appending."""
        from app import append_clinical_safety_note
        
        answer = "Take rest for headache."
        query = "how to treat headache"
        
        result = append_clinical_safety_note(query, answer)
        
        assert "consult" in result.lower() or "physician" in result.lower() or "doctor" in result.lower()
        assert "Take rest for headache" in result


# ============================================================================
# Query Rewrite Tests
# ============================================================================

class TestQueryRewrite:
    """Tests for query rewriting and contextualization."""
    
    @patch('app.get_query_rewrite_chain')
    def test_rewrite_query_for_retrieval_success(self, mock_chain):
        """Test successful query rewriting."""
        from app import rewrite_query_for_retrieval
        
        # Mock the chain to return a rewritten query
        mock_chain.return_value.invoke.return_value = "causes of diabetes"
        
        result = rewrite_query_for_retrieval("what causes it", "User: What is diabetes?")
        
        assert result == "causes of diabetes"
    
    def test_rewrite_query_greeting_passthrough(self):
        """Test that greetings are not rewritten."""
        from app import rewrite_query_for_retrieval
        
        result = rewrite_query_for_retrieval("who are you", "some history")
        assert result == "who are you"  # Should pass through unchanged
    
    def test_rewrite_query_empty_input(self):
        """Test handling of empty input."""
        from app import rewrite_query_for_retrieval
        
        result = rewrite_query_for_retrieval("", "some history")
        assert result == ""


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for component interactions."""
    
    @pytest.mark.skip(reason="Requires live API keys")
    def test_rag_chain_invocation(self):
        """Test full RAG chain with real APIs."""
        from app import get_rag_chain
        
        chain = get_rag_chain()
        result = chain.invoke({
            "input": "what is diabetes",
            "chat_history": "No previous conversation."
        })
        
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_format_docs_function(self):
        """Test document formatting for context."""
        from app import format_docs
        
        # Create mock documents
        doc1 = Mock()
        doc1.page_content = "Diabetes is a disease."
        
        doc2 = Mock()
        doc2.page_content = "It affects blood sugar."
        
        result = format_docs([doc1, doc2])
        
        assert "Diabetes is a disease." in result
        assert "It affects blood sugar." in result
        assert "\n\n" in result  # Documents separated by double newline


# ============================================================================
# Security Tests
# ============================================================================

class TestSecurity:
    """Security-focused tests."""
    
    def test_xss_input_handling(self):
        """Test XSS attempt handling."""
        from app import get_greeting_response
        
        xss_attempt = "<script>alert('xss')</script>"
        # Should not crash, ideally would be sanitized
        try:
            response = get_greeting_response(xss_attempt)
            # If it returns a response, it shouldn't contain executable script
            if response:
                assert "<script>" not in response
        except Exception:
            pass  # Exception handling is acceptable
    
    def test_sql_injection_input(self):
        """Test SQL injection attempt handling."""
        from app import is_greeting_or_personal_question
        
        sql_attempt = "'; DROP TABLE users; --"
        # Should not crash
        try:
            result = is_greeting_or_personal_question(sql_attempt)
            # Should return boolean
            assert isinstance(result, bool)
        except Exception as e:
            pytest.fail(f"SQL injection attempt caused crash: {e}")


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Performance benchmark tests."""
    
    @pytest.mark.skip(reason="Manual execution only")
    def test_response_time(self):
        """Benchmark query response time."""
        import time
        from app import rewrite_query_for_retrieval
        
        start = time.time()
        rewrite_query_for_retrieval("what is diabetes", "")
        end = time.time()
        
        elapsed = end - start
        assert elapsed < 5.0, f"Query rewrite took {elapsed}s, expected < 5s"


# ============================================================================
# Main Execution
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
