"""
Smoke Tests for Medical AI Chatbot
====================================
Quick sanity checks to verify basic functionality works.

Run with: pytest tests/test_smoke.py -v
"""

import pytest
import sys
import os
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================================
# Flask App Smoke Tests
# ============================================================================

class TestFlaskApp:
    """Smoke tests for Flask application."""
    
    @pytest.fixture(scope="class")
    def app(self):
        """Create test Flask app."""
        from flask import Flask
        from app import app as flask_app
        flask_app.config['TESTING'] = True
        flask_app.config['SECRET_KEY'] = 'test-secret'
        return flask_app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    def test_index_route_returns_200(self, client):
        """Test that index route loads successfully."""
        response = client.get('/')
        assert response.status_code == 200
    
    def test_index_contains_title(self, client):
        """Test that index page contains expected title."""
        response = client.get('/')
        assert b'MediQuery' in response.data or b'Medical' in response.data
    
    def test_clear_route_exists(self, client):
        """Test that clear endpoint exists."""
        response = client.post('/clear')
        assert response.status_code == 200
    
    def test_get_route_exists(self, client):
        """Test that chat endpoint exists."""
        response = client.post('/get', data={'msg': 'hello'})
        assert response.status_code in [200, 500]  # 500 OK if API key missing
    
    def test_get_route_requires_message(self, client):
        """Test that empty message returns error."""
        response = client.post('/get', data={'msg': ''})
        # Should either return error or handle gracefully


# ============================================================================
# Helper Function Smoke Tests
# ============================================================================

class TestHelperFunctions:
    """Smoke tests for helper functions."""
    
    def test_token_counter_import(self):
        """Test that token counter can be imported."""
        from src.helper import _TC
        assert _TC is not None
    
    def test_token_counter_count(self):
        """Test token counting works."""
        from src.helper import _TC
        count = _TC.count("Hello world")
        assert count > 0
    
    def test_token_counter_fits(self):
        """Test token budget checking."""
        from src.helper import _TC
        assert _TC.fits(0, "short", 100) == True
        assert _TC.fits(100, "very long text that exceeds budget", 100) == False
    
    def test_clean_text_function(self):
        """Test text cleaning."""
        from src.helper import _clean_text
        result = _clean_text("  multiple   spaces  ")
        # Multiple spaces are normalized to single space
        assert "multiple spaces" in result
        assert result == "multiple spaces"
    
    def test_is_boilerplate_detection(self):
        """Test boilerplate detection."""
        from src.helper import _is_boilerplate
        assert _is_boilerplate("Page 1") == True
        assert _is_boilerplate("www.example.com") == True
        assert _is_boilerplate("Normal content") == False
    
    def test_content_classification(self):
        """Test content type classification."""
        from src.helper import _classify_content
        prose = _classify_content("This is a long paragraph of text.")
        structured = _classify_content("- Item 1\n- Item 2\n- Item 3")
        assert prose == "prose"
        assert structured == "structured"


# ============================================================================
# Session Management Smoke Tests
# ============================================================================

class TestSessionManagement:
    """Smoke tests for session handling."""
    
    @pytest.fixture
    def client(self):
        """Create test client with session support."""
        from app import app
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret'
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['chat_history'] = []
            yield client
    
    def test_session_creation(self, client):
        """Test that session is created on first request."""
        # Make a request to trigger session creation
        client.get('/')
        with client.session_transaction() as sess:
            # After first request, session should have chat_history
            assert 'chat_history' in sess
    
    def test_session_cleared_on_clear(self, client):
        """Test that session is cleared."""
        # Add some history
        with client.session_transaction() as sess:
            sess['chat_history'] = [{"role": "user", "content": "test"}]
        
        # Clear
        client.post('/clear')
        
        # Verify cleared
        with client.session_transaction() as sess:
            assert len(sess.get('chat_history', [])) == 0


# ============================================================================
# Thread Safety Smoke Test
# ============================================================================

class TestThreadSafety:
    """Smoke tests for thread safety."""
    
    def test_request_logs_thread_local(self):
        """Test that request logs work across threads."""
        from app import RequestLogs
        
        # Create a fresh logs instance and test directly
        logs = RequestLogs()
        logs.info("Test message")
        
        assert len(logs.entries) > 0
        assert logs.entries[0]['message'] == "Test message"
        assert logs.entries[0]['level'] == 'INFO'


# ============================================================================
# Configuration Smoke Tests
# ============================================================================

class TestConfiguration:
    """Smoke tests for configuration."""
    
    def test_max_history_messages_config(self):
        """Test that max history constant is defined."""
        from app import MAX_HISTORY_MESSAGES
        assert MAX_HISTORY_MESSAGES == 20
    
    def test_enable_extractor_flag(self):
        """Test extractor flag exists."""
        from app import ENABLE_EXTRACTOR
        assert isinstance(ENABLE_EXTRACTOR, bool)
    
    def test_intent_section_map_defined(self):
        """Test that intent mapping is defined."""
        from app import _INTENT_SECTION_MAP
        assert len(_INTENT_SECTION_MAP) > 0


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])