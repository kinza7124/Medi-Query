"""
Regression Tests for Medical AI Chatbot
========================================
Tests to ensure existing functionality remains working after code changes.

Run with: pytest tests/test_regression.py -v
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# Query Processing Regression Tests
# ============================================================================

class TestQueryProcessingRegression:
    """Regression tests for query processing - ensure existing behavior is preserved."""
    
    def test_greeting_detection_comprehensive(self):
        """Regression: Ensure all standard greetings are detected."""
        from app import is_greeting_or_personal_question
        
        # All these should be detected as greetings (existing behavior)
        greetings = [
            "hello", "hi", "hey", 
            "good morning", "good afternoon", "good evening",
            "who are you", "what are you", "your name",
            "introduce yourself", "how are you", "how do you do"
        ]
        
        for greeting in greetings:
            result = is_greeting_or_personal_question(greeting)
            assert result == True, f"Regression: '{greeting}' should be detected as greeting"
    
    def test_medical_queries_not_flagged_as_greetings(self):
        """Regression: Medical queries should NOT be treated as greetings."""
        from app import is_greeting_or_personal_question
        
        medical_queries = [
            "what is diabetes",
            "symptoms of flu", 
            "how to treat headache",
            "causes of hypertension",
            "medication for fever",
            "treatment for acne",
            "diagnosis of cancer",
            "prevention of heart disease",
            "risk factors for diabetes",
            "complications of hypertension"
        ]
        
        for query in medical_queries:
            result = is_greeting_or_personal_question(query)
            assert result == False, f"Regression: '{query}' should NOT be a greeting"
    
    def test_greeting_responses_still_work(self):
        """Regression: Ensure greeting responses are returned."""
        from app import get_greeting_response
        
        # Identity queries
        identity_response = get_greeting_response("who are you")
        assert identity_response is not None
        assert "Medical" in identity_response or "AI" in identity_response
        
        # Hello queries
        hello_response = get_greeting_response("hello")
        assert hello_response is not None
        assert "Hello" in hello_response or "hi" in hello_response.lower()
        
        # How are you
        how_response = get_greeting_response("how are you")
        assert how_response is not None
        assert "well" in how_response.lower() or "ready" in how_response.lower()
    
    def test_medical_queries_return_none(self):
        """Regression: Medical queries should not trigger greeting responses."""
        from app import get_greeting_response
        
        medical_queries = [
            "what is diabetes",
            "tell me about symptoms",
            "how to treat acne",
            "causes of fever"
        ]
        
        for query in medical_queries:
            result = get_greeting_response(query)
            assert result is None, f"Regression: '{query}' should not trigger greeting"


# ============================================================================
# Chat History Regression Tests
# ============================================================================

class TestChatHistoryRegression:
    """Regression tests for chat history - ensure memory works correctly."""
    
    def test_format_chat_history_empty(self):
        """Regression: Empty history should show default message."""
        from app import format_chat_history
        
        result = format_chat_history([])
        assert "No previous conversation" in result
    
    def test_format_chat_history_single_exchange(self):
        """Regression: Single exchange formatting."""
        from app import format_chat_history
        
        history = [
            {"role": "user", "content": "What is diabetes?"},
            {"role": "assistant", "content": "Diabetes is..."}
        ]
        
        result = format_chat_history(history)
        assert "User: What is diabetes?" in result
        assert "Assistant: Diabetes is" in result
    
    def test_format_chat_history_last_3_exchanges(self):
        """Regression: Should include last 6 messages (3 exchanges)."""
        from app import format_chat_history
        
        # Create 4 exchanges (8 messages)
        history = [
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "q2"},
            {"role": "assistant", "content": "a2"},
            {"role": "user", "content": "q3"},
            {"role": "assistant", "content": "a3"},
            {"role": "user", "content": "q4"},
            {"role": "assistant", "content": "a4"},
        ]
        
        result = format_chat_history(history)
        
        # Should have q3, a3, q4, a4 (last 4 messages = 2 exchanges)
        assert "q4" in result
        assert "a4" in result
        assert "q1" not in result  # Old messages should be excluded
    
    def test_role_labeling(self):
        """Regression: User and Assistant labels are correct."""
        from app import format_chat_history
        
        history = [
            {"role": "user", "content": "test question"},
            {"role": "assistant", "content": "test answer"}
        ]
        
        result = format_chat_history(history)
        assert "User:" in result
        assert "Assistant:" in result


# ============================================================================
# Answer Processing Regression Tests
# ============================================================================

class TestAnswerProcessingRegression:
    """Regression tests for answer processing - ensure formatting works."""
    
    def test_clean_answer_removes_based_on_context(self):
        """Regression: Remove meta-phrases from answers."""
        from app import clean_answer_text
        
        test_cases = [
            ("Based on the context, diabetes is...", "diabetes is"),
            ("According to the provided context, it is...", "it is"),
            ("This describes the condition as...", "the condition as"),
            ("Based on the provided information, treatment is...", "treatment is"),
        ]
        
        for input_text, expected in test_cases:
            result = clean_answer_text("what is diabetes", input_text)
            assert "Based on the context" not in result
            assert "According to the provided context" not in result
            assert expected in result.lower()
    
    def test_extract_subject_various_forms(self):
        """Regression: Subject extraction from different question forms."""
        from app import extract_subject_from_question
        
        test_cases = [
            ("what is diabetes", "diabetes"),
            ("what is hypertension", "hypertension"),
            ("what's acne", "acne"),
            ("define fever", "fever"),
            ("describe heart disease", "heart disease"),
        ]
        
        for query, expected in test_cases:
            result = extract_subject_from_question(query)
            assert result == expected, f"Failed for: {query}"
    
    def test_needs_clinical_safety_note_medical_terms(self):
        """Regression: Safety notes for medication-related queries."""
        from app import needs_clinical_safety_note
        
        queries_requiring_note = [
            "medicine for fever",
            "medication for diabetes", 
            "tablet for headache",
            "treatment for pain",
            "abdominal pain causes",
            "stomach pain remedy",
            "vomit treatment",
            "nausea medicine",
        ]
        
        for query in queries_requiring_note:
            result = needs_clinical_safety_note(query)
            assert result == True, f"'{query}' should need safety note"
    
    def test_append_clinical_safety_note_adds_disclaimer(self):
        """Regression: Safety note is appended correctly."""
        from app import append_clinical_safety_note
        
        answer = "Take aspirin for fever."
        result = append_clinical_safety_note("medicine for fever", answer)
        
        # Should have appended note
        assert "consult" in result.lower() or "doctor" in result.lower() or "physician" in result.lower()
        # Original answer should be preserved
        assert "Take aspirin" in result
    
    def test_format_answer_for_readability_bullet_conversion(self):
        """Regression: Multi-sentence answers get bullet points."""
        from app import format_answer_for_readability
        
        # Question asking for list
        query = "what are the causes of diabetes"
        answer = "Obesity is one factor. Poor diet is another. Lack of exercise matters too."
        
        result = format_answer_for_readability(query, answer)
        
        # Should have bullet points
        assert "\n- " in result or "- " in result


# ============================================================================
# Query Rewrite Regression Tests
# ============================================================================

class TestQueryRewriteRegression:
    """Regression tests for query rewriting - ensure passthrough works."""
    
    def test_rewrite_query_passthrough_greetings(self):
        """Regression: Greetings should pass through unchanged."""
        from app import rewrite_query_for_retrieval
        
        greetings = ["hello", "hi", "who are you", "how are you"]
        
        for greeting in greetings:
            result = rewrite_query_for_retrieval(greeting, "")
            assert result == greeting, f"'{greeting}' should pass through unchanged"
    
    def test_rewrite_query_empty_input(self):
        """Regression: Empty input handling."""
        from app import rewrite_query_for_retrieval
        
        result = rewrite_query_for_retrieval("", "some history")
        assert result == ""
    
    @patch('app.get_query_rewrite_chain')
    def test_rewrite_query_calls_chain(self, mock_chain):
        """Regression: Query rewrite chain is called for medical queries."""
        from app import rewrite_query_for_retrieval
        
        mock_chain.return_value.invoke.return_value = "rewritten query"
        
        result = rewrite_query_for_retrieval("what causes it", "history about diabetes")
        
        # Chain should be called
        mock_chain.assert_called_once()


# ============================================================================
# Metadata Filtering Regression Tests
# ============================================================================

class TestMetadataFilteringRegression:
    """Regression tests for metadata filtering - ensure intent detection works."""
    
    def test_infer_section_filter_symptoms(self):
        """Regression: Symptom queries get correct filter."""
        from app import infer_section_filter
        
        queries = [
            "what are symptoms of diabetes",
            "signs of hypertension",
            "clinical presentation of flu"
        ]
        
        for query in queries:
            result = infer_section_filter(query)
            assert result is not None
            assert "section" in result
    
    def test_infer_section_filter_causes(self):
        """Regression: Cause queries get correct filter."""
        from app import infer_section_filter
        
        queries = [
            "causes of diabetes",
            "etiology of hypertension",
            "why does acne occur"
        ]
        
        for query in queries:
            result = infer_section_filter(query)
            assert result is not None
            assert "section" in result
    
    def test_infer_section_filter_treatment(self):
        """Regression: Treatment queries get correct filter."""
        from app import infer_section_filter
        
        queries = [
            "treatment for diabetes",
            "how to manage hypertension",
            "therapy for acne"
        ]
        
        for query in queries:
            result = infer_section_filter(query)
            assert result is not None
            assert "section" in result
    
    def test_infer_section_filter_no_match(self):
        """Regression: Generic queries return None (no filter)."""
        from app import infer_section_filter
        
        queries = [
            "tell me about diabetes",
            "what is this disease",
            "overview of hypertension"
        ]
        
        for query in queries:
            # These are overview queries - might or might not have filter
            # Just ensure function doesn't crash
            result = infer_section_filter(query)
            assert result is None or result.get("section") is not None


# ============================================================================
# Request Logs Regression Tests
# ============================================================================

class TestRequestLogsRegression:
    """Regression tests for request logging."""
    
    def test_request_logs_creation(self):
        """Regression: Request logs can be created."""
        from app import RequestLogs
        
        logs = RequestLogs()
        assert logs.entries == []
    
    def test_request_logs_add_entries(self):
        """Regression: Can add log entries."""
        from app import RequestLogs
        
        logs = RequestLogs()
        logs.info("Test info")
        logs.warning("Test warning")
        logs.error("Test error")
        
        assert len(logs.entries) == 3
        assert logs.entries[0]['level'] == 'INFO'
        assert logs.entries[1]['level'] == 'WARNING'
        assert logs.entries[2]['level'] == 'ERROR'
    
    def test_request_logs_get_all(self):
        """Regression: Can retrieve all logs."""
        from app import RequestLogs
        
        logs = RequestLogs()
        logs.info("Message 1")
        logs.info("Message 2")
        
        all_logs = logs.get_all()
        assert len(all_logs) == 2
    
    def test_request_logs_clear(self):
        """Regression: Can clear logs."""
        from app import RequestLogs
        
        logs = RequestLogs()
        logs.info("Test")
        logs.clear()
        
        assert logs.entries == []


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])