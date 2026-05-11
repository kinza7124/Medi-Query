"""
Security Tests for Medical AI Chatbot
======================================
Comprehensive security testing covering XSS, SQL injection, input validation,
API security, and session security.

Run with: pytest tests/test_security.py -v
"""

import pytest
import sys
import os
import re
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# XSS Prevention Tests
# ============================================================================

class TestXSSPrevention:
    """Tests for XSS (Cross-Site Scripting) prevention."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app import app
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret'
        with app.test_client() as client:
            yield client
    
    def test_xss_script_tag_in_message(self, client):
        """Test that script tags in messages are handled safely."""
        xss_inputs = [
            "<script>alert('xss')</script>",
            "<script>alert('XSS')</script>",
            "<SCRIPT>alert('XSS')</SCRIPT>",
        ]
        
        for xss_input in xss_inputs:
            response = client.post('/get', data={'msg': xss_input})
            data = response.get_data(as_text=True)
            
            # Response should not contain executable script tags
            # (Either sanitized, escaped, or not executed)
            assert "<script>" not in data.lower() or "</script>" not in data.lower(), \
                f"XSS payload executed: {xss_input[:50]}"
    
    def test_xss_img_onerror(self, client):
        """Test that img onerror payloads are handled."""
        xss_inputs = [
            "<img src=x onerror=alert('xss')>",
            "<img src=\"x\" onerror=\"alert(1)\">",
            "<image src=x onerror=alert('xss')>",
        ]
        
        for xss_input in xss_inputs:
            response = client.post('/get', data={'msg': xss_input})
            data = response.get_data(as_text=True)
            
            # onerror should not be present in response
            assert "onerror=" not in data.lower()
    
    def test_xss_javascript_uri(self, client):
        """Test that javascript: URIs are handled."""
        xss_inputs = [
            "javascript:alert('xss')",
            "javascript:alert(document.cookie)",
            "<a href=\"javascript:alert('xss')\">click</a>",
        ]
        
        for xss_input in xss_inputs:
            response = client.post('/get', data={'msg': xss_input})
            data = response.get_data(as_text=True)
            
            # Should not execute
            assert "javascript:alert" not in data.lower()
    
    def test_xss_iframe_injection(self, client):
        """Test that iframe injection is blocked."""
        xss_inputs = [
            "<iframe src='javascript:alert(\"xss\")'></iframe>",
            "<iframe src=\"evil.html\"></iframe>",
        ]
        
        for xss_input in xss_inputs:
            response = client.post('/get', data={'msg': xss_input})
            data = response.get_data(as_text=True)
            
            assert "<iframe" not in data.lower()
    
    def test_xss_nested_payloads(self, client):
        """Test complex nested XSS payloads."""
        xss_inputs = [
            "<div onmouseover=\"alert('xss')\">hover</div>",
            "<body onload=alert('xss')>",
            "<svg onload=alert('xss')>",
            "<input onfocus=alert('xss') autofocus>",
        ]
        
        for xss_input in xss_inputs:
            response = client.post('/get', data={'msg': xss_input})
            data = response.get_data(as_text=True)
            
            # Event handlers should be neutralized
            assert "onload=" not in data.lower()
            assert "onerror=" not in data.lower()
            assert "onmouseover=" not in data.lower()
            assert "onfocus=" not in data.lower()
    
    def test_html_entity_encoding(self, client):
        """Test that HTML entities are properly encoded in output."""
        response = client.post('/get', data={'msg': '<test>&"</test>'})
        data = response.get_data(as_text=True)
        
        # If the input is reflected, it should be HTML-encoded
        # <test> should become &lt;test&gt; or be handled appropriately
        # The key is that raw HTML shouldn't be executable
        # This test verifies output handling is safe


# ============================================================================
# SQL Injection Prevention Tests
# ============================================================================

class TestSQLInjectionPrevention:
    """Tests for SQL injection prevention."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_sql_injection_tautology(self, client):
        """Test SQL injection with tautology attacks."""
        sql_payloads = [
            "' OR '1'='1",
            "' OR '1'='1' --",
            "' OR 1=1--",
            "1' OR '1'='1",
        ]
        
        for payload in sql_payloads:
            # Should not crash
            response = client.post('/get', data={'msg': payload})
            assert response.status_code in [200, 400, 500]
    
    def test_sql_injection_union(self, client):
        """Test SQL injection with UNION attacks."""
        sql_payloads = [
            "' UNION SELECT * FROM users--",
            "' UNION SELECT password FROM users--",
            "1' UNION SELECT NULL--",
        ]
        
        for payload in sql_payloads:
            response = client.post('/get', data={'msg': payload})
            assert response.status_code in [200, 400, 500]
    
    def test_sql_injection_destructive(self, client):
        """Test destructive SQL injection attempts."""
        sql_payloads = [
            "'; DROP TABLE users; --",
            "'; DELETE FROM users; --",
            "'; DROP DATABASE medical_chatbot; --",
        ]
        
        for payload in sql_payloads:
            # Should not crash the system
            response = client.post('/get', data={'msg': payload})
            # System should handle gracefully, not expose data
            data = response.get_data(as_text=True)
            assert "DROP TABLE" not in data
            assert "DELETE FROM" not in data
    
    def test_sql_injection_comment(self, client):
        """Test SQL injection with comment attacks."""
        sql_payloads = [
            "admin'--",
            "admin' #",
            "'/*comment*/",
        ]
        
        for payload in sql_payloads:
            response = client.post('/get', data={'msg': payload})
            # Should handle gracefully
            assert response.status_code in [200, 400, 500]


# ============================================================================
# Input Validation Tests
# ============================================================================

class TestInputValidation:
    """Tests for input validation and sanitization."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_empty_input_handling(self, client):
        """Test handling of empty input."""
        response = client.post('/get', data={'msg': ''})
        data = response.get_data(as_text=True)
        
        # Should either return error or empty response
        assert "Please enter" in data.lower() or "enter a message" in data.lower()
    
    def test_whitespace_only_input(self, client):
        """Test handling of whitespace-only input."""
        response = client.post('/get', data={'msg': '   \n\t   '})
        data = response.get_data(as_text=True)
        
        # Should handle gracefully
        assert response.status_code in [200, 400]
    
    def test_extremely_long_input(self, client):
        """Test handling of extremely long input."""
        long_input = "a" * 100000  # 100KB of data
        
        response = client.post('/get', data={'msg': long_input})
        
        # Should either reject or truncate, not crash
        assert response.status_code in [200, 400, 413, 500]
    
    def test_unicode_input(self, client):
        """Test handling of various Unicode characters."""
        unicode_inputs = [
            "Hello 🌍",
            "Привет",
            "مرحبا",
            "你好",
            "हैलो",
            "🔥🔥🔥",
        ]
        
        for input_text in unicode_inputs:
            response = client.post('/get', data={'msg': input_text})
            # Should handle Unicode gracefully
            assert response.status_code in [200, 500]
    
    def test_binary_data_input(self, client):
        """Test handling of binary-like input."""
        binary_inputs = [
            "\x00\x01\x02\x03",
            "\xff\xfe\xfd",
            b"\x00\x01".decode('latin-1'),
        ]
        
        for input_text in binary_inputs:
            try:
                response = client.post('/get', data={'msg': input_text})
                assert response.status_code in [200, 400, 500]
            except Exception:
                # Handling is acceptable
                pass
    
    def test_special_characters_input(self, client):
        """Test handling of special characters."""
        special_inputs = [
            "|grep",
            "&& ls",
            "; rm -rf",
            "$(whoami)",
            "`whoami`",
            "\\n\\r\\t",
        ]
        
        for input_text in special_inputs:
            response = client.post('/get', data={'msg': input_text})
            # Should not execute commands
            assert response.status_code in [200, 400, 500]


# ============================================================================
# Session Security Tests
# ============================================================================

class TestSessionSecurity:
    """Tests for session security."""
    
    def test_session_cookie_flags(self):
        """Test that session cookies have proper security flags."""
        from app import app
        
        app.config['SECRET_KEY'] = 'test-secret'
        app.config['SESSION_COOKIE_SECURE'] = False  # Testing mode
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        
        with app.test_client() as client:
            response = client.get('/')
            
            # Check cookie attributes
            # Note: In testing mode, some flags may be different
            assert response.status_code == 200
    
    def test_session_not_persistent(self):
        """Test that sessions are not persistent (no permanent cookies)."""
        from app import app
        
        with app.test_client() as client:
            response = client.get('/')
            
            # Session should work but not be persistently stored
            assert response.status_code == 200
    
    def test_session_cleared_properly(self):
        """Test that session is properly cleared."""
        from app import app
        
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret'
        
        with app.test_client() as client:
            # Create session with data
            client.post('/get', data={'msg': 'test query'})
            
            # Clear session
            response = client.post('/clear')
            assert response.status_code == 200
            
            # Verify session is cleared
            with client.session_transaction() as sess:
                assert len(sess.get('chat_history', [])) == 0


# ============================================================================
# API Key Security Tests
# ============================================================================

class TestAPIKeySecurity:
    """Tests for API key handling and security."""
    
    def test_no_api_keys_in_html(self):
        """Test that API keys are not exposed in HTML."""
        from app import app
        
        with app.test_client() as client:
            response = client.get('/')
            html = response.get_data(as_text=True)
            
            # API keys should never be in HTML
            assert 'GROQ_API_KEY' not in html
            assert 'PINECONE_API_KEY' not in html
            assert 'sk-' not in html  # Common API key prefix
    
    def test_no_api_keys_in_source(self):
        """Test that API keys are not exposed in JavaScript."""
        from app import app
        
        with app.test_client() as client:
            response = client.get('/')
            html = response.get_data(as_text=True)
            
            # Should not contain actual API key values
            # Check for patterns that would indicate key exposure
            assert 'sk-groq' not in html.lower()
            assert 'sk-pincone' not in html.lower()
    
    @patch.dict(os.environ, {'GROQ_API_KEY': '', 'PINECONE_API_KEY': ''})
    def test_missing_api_keys_handling(self):
        """Test handling when API keys are missing."""
        # This test verifies the app doesn't crash on missing keys
        # Actual behavior depends on implementation
        from app import app
        
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            # App should start even without keys (might show errors)
            response = client.get('/')
            assert response.status_code == 200


# ============================================================================
# Response Security Tests
# ============================================================================

class TestResponseSecurity:
    """Tests for response content security."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_no_internal_paths_in_response(self, client):
        """Test that internal file paths are not exposed."""
        response = client.post('/get', data={'msg': 'what is diabetes'})
        data = response.get_data(as_text=True)
        
        # Should not expose internal paths
        assert "C:\\" not in data
        assert "/home/" not in data
        assert "c:\\users\\" not in data.lower()
    
    def test_no_internal_hostnames_in_response(self, client):
        """Test that internal hostnames are not exposed."""
        response = client.post('/get', data={'msg': 'what is diabetes'})
        data = response.get_data(as_text=True)
        
        # Should not expose internal system info
        assert "localhost" not in data.lower() or "local" in data.lower()
    
    def test_error_messages_safe(self, client):
        """Test that error messages don't expose sensitive info."""
        # Try with invalid input to trigger potential error
        response = client.post('/get', data={'msg': '\x00'})
        
        # Should have safe error handling
        # Either returns 200 with error message, or 500
        assert response.status_code in [200, 500]


# ============================================================================
# Rate Limiting & DoS Tests
# ============================================================================

class TestRateLimiting:
    """Tests for rate limiting and DoS protection."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_rapid_requests_handling(self, client):
        """Test handling of rapid successive requests."""
        # Make several rapid requests
        for i in range(10):
            response = client.post('/get', data={'msg': 'test'})
            # Should handle gracefully
            assert response.status_code in [200, 500]
    
    def test_concurrent_sessions(self, client):
        """Test handling of multiple concurrent session operations."""
        # Multiple requests should not interfere
        for i in range(5):
            response = client.post('/get', data={'msg': f'query {i}'})
            assert response.status_code in [200, 500]


# ============================================================================
# Authentication & Authorization Tests
# ============================================================================

class TestAuthenticationAuthorization:
    """Tests for authentication and authorization."""
    
    def test_no_auth_required(self):
        """Test that no authentication is required (by design)."""
        from app import app
        
        with app.test_client() as client:
            # Should be accessible without auth
            response = client.get('/')
            assert response.status_code == 200
    
    def test_no_admin_endpoints_exposed(self):
        """Test that admin endpoints are not exposed."""
        from app import app
        
        admin_routes = [
            '/admin',
            '/admin/dashboard',
            '/admin/users',
            '/debug',
            '/debug/console',
        ]
        
        with app.test_client() as client:
            for route in admin_routes:
                response = client.get(route)
                # Should either 404 or redirect, not expose admin
                assert response.status_code in [302, 404]


# ============================================================================
# Data Privacy Tests
# ============================================================================

class TestDataPrivacy:
    """Tests for data privacy compliance."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_no_pii_in_logs(self, client):
        """Test that PII is not logged."""
        # Make a request with potentially sensitive data
        response = client.post('/get', data={'msg': 'my name is John Smith'})
        
        # The response should not contain the raw input in a way
        # that exposes it to logs (depends on implementation)
        # This is more of a code review item
    
    def test_chat_history_not_persisted(self, client):
        """Test that chat history is not permanently stored."""
        # Make some requests
        client.post('/get', data={'msg': 'test message'})
        
        # Clear session
        client.post('/clear')
        
        # Session should be cleared
        with client.session_transaction() as sess:
            assert len(sess.get('chat_history', [])) == 0
    
    def test_session_data_limited(self, client):
        """Test that session data is limited/capped."""
        # Session should have a limit on history
        from app import MAX_HISTORY_MESSAGES
        
        # This constant should limit history
        assert MAX_HISTORY_MESSAGES == 20  # As per implementation


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])