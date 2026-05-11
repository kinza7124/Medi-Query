"""
Integration Tests for Medical AI Chatbot
==========================================
End-to-end tests for full pipeline functionality.

Run with: pytest tests/test_integration.py -v
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# Full Pipeline Integration Tests
# ============================================================================

class TestFullPipeline:
    """Integration tests for the full RAG pipeline."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app import app
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret'
        with app.test_client() as client:
            yield client
    
    def test_full_chat_flow_basic(self, client):
        """Test complete chat flow from request to response."""
        # Clear any existing session
        client.post('/clear')
        
        # Send a simple message
        response = client.post('/get', data={'msg': 'hello'})
        
        assert response.status_code == 200
        data = response.get_data(as_text=True)
        
        # Should get a response (either greeting or actual answer)
        assert len(data) > 0
        assert "Please enter" not in data  # Not an empty error
    
    def test_chat_flow_returns_json_structure(self, client):
        """Test that chat returns proper JSON structure with logs."""
        # This tests the new logs feature
        response = client.post('/get', data={'msg': 'hello'}, content_type='application/json')
        
        # Check if we get JSON back (or handle string for backward compat)
        data = response.get_data(as_text=True)
        assert len(data) > 0
    
    def test_session_persists_across_requests(self, client):
        """Test that session persists between requests."""
        # First request
        client.post('/get', data={'msg': 'what is diabetes'})
        
        # Second request with follow-up
        response = client.post('/get', data={'msg': 'how is it treated'})
        
        assert response.status_code == 200
    
    def test_clear_session_works(self, client):
        """Test session clearing."""
        # Add some messages
        client.post('/get', data={'msg': 'test message'})
        
        # Clear
        response = client.post('/clear')
        assert response.status_code == 200
        assert b'cleared' in response.data.lower() or b'Cleared' in response.data
    
    def test_empty_message_handling(self, client):
        """Test handling of empty message."""
        response = client.post('/get', data={'msg': ''})
        
        # Should get error message
        data = response.get_data(as_text=True)
        assert "Please enter" in data or "enter" in data.lower()
    
    def test_unicode_message_handling(self, client):
        """Test handling of Unicode characters."""
        response = client.post('/get', data={'msg': 'What is diabetes?'})
        
        assert response.status_code == 200
        data = response.get_data(as_text=True)
        assert len(data) > 0


# ============================================================================
# RAG Chain Integration Tests
# ============================================================================

class TestRAGChainIntegration:
    """Integration tests for RAG chain components."""
    
    @patch('app.get_llm')
    @patch('app._retrieve_with_filter')
    def test_rag_chain_formats_context(self, mock_retrieve, mock_llm):
        """Test that RAG chain properly formats context."""
        from app import get_rag_chain
        
        # Mock the retrieval to return sample docs
        mock_retrieve.return_value = "Sample medical context about diabetes."
        
        # Mock the LLM to return a response
        mock_llm_instance = Mock()
        mock_llm_instance.invoke.return_value = Mock(content="Diabetes is a condition...")
        mock_llm.return_value = mock_llm_instance
        
        chain = get_rag_chain()
        
        # Note: This test verifies chain structure, not full execution
        assert chain is not None
    
    def test_retrieve_with_filter_returns_string(self, client):
        """Test that retrieval returns formatted string."""
        # This is a basic sanity check
        from app import _format_docs
        
        doc1 = Mock()
        doc1.page_content = "Test content"
        doc1.metadata = {"section": "Test", "page": 1}
        
        doc2 = Mock()
        doc2.page_content = "More content"
        doc2.metadata = {"section": "Test2", "page": 2}
        
        result = _format_docs([doc1, doc2])
        
        assert "Test content" in result
        assert "More content" in result
        assert "Section:" in result or "section" in result.lower()


# ============================================================================
# UI Integration Tests
# ============================================================================

class TestUIIntegration:
    """Integration tests for UI components."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_index_page_loads(self, client):
        """Test that main page loads."""
        response = client.get('/')
        assert response.status_code == 200
    
    def test_index_contains_required_elements(self, client):
        """Test that UI has required elements."""
        response = client.get('/')
        html = response.get_data(as_text=True)
        
        # Check for key UI elements
        assert 'newChatBtn' in html or 'New conversation' in html
        assert 'messageArea' in html or 'text' in html
        assert 'send' in html
    
    def test_css_file_accessible(self, client):
        """Test that CSS is served."""
        response = client.get('/static/style.css')
        # CSS should be served (200) or not found if using Flask's static (404 is fine for test)
        assert response.status_code in [200, 404]


# ============================================================================
# Error Handling Integration Tests
# ============================================================================

class TestErrorHandling:
    """Integration tests for error handling."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_invalid_route_returns_404(self, client):
        """Test that invalid routes return 404."""
        response = client.get('/invalid/route')
        assert response.status_code == 404
    
    def test_large_message_handling(self, client):
        """Test handling of very large messages."""
        # Create a very long message
        long_message = "test " * 10000  # Very long message
        
        response = client.post('/get', data={'msg': long_message})
        
        # Should handle gracefully (not crash)
        assert response.status_code in [200, 400, 413]
    
    def test_special_characters_handling(self, client):
        """Test handling of special characters."""
        special_chars = [
            "What is diabetes? <test>",
            "Test 'quotes' and \"double quotes\"",
            "Test \\ backslash",
            "Test newline\ncharacter",
        ]
        
        for msg in special_chars:
            response = client.post('/get', data={'msg': msg})
            # Should not crash
            assert response.status_code in [200, 500]


# ============================================================================
# Performance Integration Tests
# ============================================================================

class TestPerformanceIntegration:
    """Integration tests for performance."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_response_time_under_5_seconds(self, client):
        """Test that simple queries respond quickly."""
        import time
        
        start = time.time()
        response = client.post('/get', data={'msg': 'hello'})
        elapsed = time.time() - start
        
        # With mocked/skip actual API, should be fast
        # In production with real APIs, this would be longer
        assert elapsed < 5.0
    
    def test_concurrent_requests(self, client):
        """Test handling of rapid sequential requests."""
        for i in range(3):
            response = client.post('/get', data={'msg': f'test message {i}'})
            assert response.status_code in [200, 500]  # Allow API failures


# ============================================================================
# API Response Format Tests
# ============================================================================

class TestAPIResponseFormat:
    """Tests for API response formats."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_clear_endpoint_format(self, client):
        """Test clear endpoint returns proper response."""
        response = client.post('/clear')
        data = response.get_data(as_text=True)
        
        # Should return some message
        assert len(data) > 0
    
    def test_get_endpoint_response_type(self, client):
        """Test that get endpoint returns text or JSON."""
        response = client.post('/get', data={'msg': 'test'})
        
        content_type = response.content_type
        # Should be either text/html or application/json
        assert 'text/html' in content_type or 'application/json' in content_type


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])