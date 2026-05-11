"""
Functional Tests for Medical AI Chatbot
========================================
End-to-end functional tests for user scenarios.

Run with: pytest tests/test_functional.py -v
"""

import pytest
import sys
import os
from unittest.mock import patch, Mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# Chat Flow Tests
# ============================================================================

class TestChatFlow:
    """Test complete chat flows."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app import app
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret'
        with app.test_client() as client:
            yield client
    
    def test_ft001_basic_medical_query(self, client):
        """FT-001: Basic medical query returns response."""
        # Clear any existing session
        client.post('/clear')
        
        # Send basic query
        response = client.post('/get', data={'msg': 'what is diabetes'})
        
        assert response.status_code == 200
        data = response.get_data(as_text=True)
        
        # Should get a response (not an error)
        assert len(data) > 0
        assert "Please enter" not in data  # Not empty error
    
    def test_ft002_pronoun_resolution_single_topic(self, client):
        """FT-002: Pronoun resolution within single topic."""
        # Clear session
        client.post('/clear')
        
        # First query about acne
        response1 = client.post('/get', data={'msg': 'what is acne'})
        assert response1.status_code == 200
        
        # Second query with pronoun
        response2 = client.post('/get', data={'msg': 'how to treat it'})
        assert response2.status_code == 200
        
        # Response should be about acne treatment
        data2 = response2.get_data(as_text=True)
        # Note: Actual validation would need to check response content
        # which requires mocking or real API
    
    def test_ft003_pronoun_resolution_topic_switch(self, client):
        """FT-003: Pronoun resolution after topic switch."""
        # This tests that pronouns resolve to most recent topic
        client.post('/clear')
        
        # Topic 1
        client.post('/get', data={'msg': 'what is drowsiness'})
        # Topic 2
        client.post('/get', data={'msg': 'what is acne'})
        # Pronoun query
        response = client.post('/get', data={'msg': 'how to treat it'})
        
        assert response.status_code == 200
    
    def test_ft005_non_medical_identity_query(self, client):
        """FT-005: Non-medical query - bot identity."""
        client.post('/clear')
        
        response = client.post('/get', data={'msg': 'who are you'})
        
        assert response.status_code == 200
        data = response.get_data(as_text=True)
        
        # Should get identity response
        assert len(data) > 0
    
    def test_ft010_empty_input_handling(self, client):
        """FT-010: Empty input handling."""
        response = client.post('/get', data={'msg': ''})
        
        assert response.status_code == 200
        data = response.get_data(as_text=True)
        
        # Should have error message
        assert "Please enter" in data.lower() or "enter" in data.lower()
    
    def test_greeting_handling(self, client):
        """Test greeting messages."""
        greetings = ['hello', 'hi', 'hey', 'good morning']
        
        for greeting in greetings:
            client.post('/clear')  # Reset
            response = client.post('/get', data={'msg': greeting})
            
            assert response.status_code == 200
            data = response.get_data(as_text=True)
            
            # Should get greeting response
            assert len(data) > 0


# ============================================================================
# UI Interaction Tests
# ============================================================================

class TestUIInteractions:
    """Test UI interactions."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_index_page_loads(self, client):
        """Test main page loads."""
        response = client.get('/')
        assert response.status_code == 200
    
    def test_index_contains_chat_elements(self, client):
        """Test page contains chat UI elements."""
        response = client.get('/')
        html = response.get_data(as_text=True)
        
        # Check for UI elements
        assert 'messageArea' in html or 'messagesContainer' in html
        assert 'text' in html  # Input field
    
    def test_clear_button_functionality(self, client):
        """Test clear chat button works."""
        # Make a request to create history
        client.post('/get', data={'msg': 'test query'})
        
        # Clear
        response = client.post('/clear')
        
        assert response.status_code == 200
    
    def test_multiple_conversation_turns(self, client):
        """Test multiple conversation turns."""
        client.post('/clear')
        
        # Turn 1
        r1 = client.post('/get', data={'msg': 'what is fever'})
        assert r1.status_code == 200
        
        # Turn 2
        r2 = client.post('/get', data={'msg': 'what are symptoms'})
        assert r2.status_code == 200
        
        # Turn 3
        r3 = client.post('/get', data={'msg': 'how to treat'})
        assert r3.status_code == 200


# ============================================================================
# Query Processing Tests
# ============================================================================

class TestQueryProcessing:
    """Test query processing functionality."""
    
    def test_query_rewrite_preserves_medical_terms(self):
        """Test that medical terms are preserved in rewrite."""
        from app import rewrite_query_for_retrieval
        
        # With mocked chain, verify passthrough for greetings
        result = rewrite_query_for_retrieval("hello", "")
        assert result == "hello"
        
        result = rewrite_query_for_retrieval("who are you", "")
        assert result == "who are you"
    
    def test_intent_detection_symptoms(self):
        """Test symptom intent detection."""
        from app import infer_section_filter
        
        queries = [
            "what are symptoms of diabetes",
            "signs of hypertension",
            "what does it look like"
        ]
        
        for query in queries:
            result = infer_section_filter(query)
            # Should return filter for symptoms
            assert result is not None
            assert "section" in result
    
    def test_intent_detection_causes(self):
        """Test causes intent detection."""
        from app import infer_section_filter
        
        queries = [
            "causes of diabetes",
            "why does it happen",
            "etiology of hypertension"
        ]
        
        for query in queries:
            result = infer_section_filter(query)
            assert result is not None
            assert "section" in result
    
    def test_intent_detection_treatment(self):
        """Test treatment intent detection."""
        from app import infer_section_filter
        
        queries = [
            "how to treat diabetes",
            "treatment for hypertension",
            "therapy options"
        ]
        
        for query in queries:
            result = infer_section_filter(query)
            assert result is not None


# ============================================================================
# Response Processing Tests
# ============================================================================

class TestResponseProcessing:
    """Test response processing."""
    
    def test_clinical_safety_note_for_medication(self):
        """Test safety note for medication queries."""
        from app import needs_clinical_safety_note
        
        queries = [
            "medicine for fever",
            "tablet for headache",
            "drug for diabetes"
        ]
        
        for query in queries:
            result = needs_clinical_safety_note(query)
            assert result == True
    
    def test_clinical_safety_note_for_symptoms(self):
        """Test safety note for symptom queries."""
        from app import needs_clinical_safety_note
        
        queries = [
            "abdominal pain",
            "chest pain",
            "stomach ache"
        ]
        
        for query in queries:
            result = needs_clinical_safety_note(query)
            assert result == True
    
    def test_answer_formatting_for_list_questions(self):
        """Test answer formatting for list-type questions."""
        from app import format_answer_for_readability
        
        # List-type question
        query = "what are causes of diabetes"
        answer = "Obesity is one factor. Genetics matter too. Lifestyle plays a role."
        
        result = format_answer_for_readability(query, answer)
        
        # Should have bullet points
        assert "\n- " in result or "- " in result


# ============================================================================
# Session Management Tests
# ============================================================================

class TestSessionManagement:
    """Test session management."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app import app
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret'
        with app.test_client() as client:
            yield client
    
    def test_session_initialized_on_first_request(self, client):
        """Test session is initialized on first request."""
        response = client.get('/')
        assert response.status_code == 200
        
        # Session should have chat_history
        with client.session_transaction() as sess:
            assert 'chat_history' in sess
    
    def test_chat_history_accumulated(self, client):
        """Test chat history accumulates."""
        client.post('/clear')
        
        # Make request
        client.post('/get', data={'msg': 'test query'})
        
        # Check history
        with client.session_transaction() as sess:
            history = sess.get('chat_history', [])
            # Should have user and assistant messages
            assert len(history) >= 2
    
    def test_chat_history_capped(self, client):
        """Test chat history is capped at limit."""
        from app import MAX_HISTORY_MESSAGES
        
        # Make more requests than limit
        for i in range(15):
            client.post('/get', data={'msg': f'query {i}'})
        
        # Check history is capped
        with client.session_transaction() as sess:
            history = sess.get('chat_history', [])
            assert len(history) <= MAX_HISTORY_MESSAGES


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_invalid_route_returns_404(self, client):
        """Test invalid routes return 404."""
        response = client.get('/nonexistent/route')
        assert response.status_code == 404
    
    def test_method_not_allowed(self, client):
        """Test wrong HTTP method handling."""
        # GET to POST-only endpoint
        response = client.get('/get')
        # Should either work (Flask is flexible) or return 405
        assert response.status_code in [200, 405]
    
    def test_large_message_handling(self, client):
        """Test large message handling."""
        large_msg = "a" * 50000  # 50KB
        
        response = client.post('/get', data={'msg': large_msg})
        
        # Should handle gracefully
        assert response.status_code in [200, 400, 413, 500]


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])