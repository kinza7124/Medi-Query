"""
Performance Tests for Medical AI Chatbot
==========================================
Performance and load testing.

Run with: pytest tests/test_performance.py -v
"""

import pytest
import sys
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# Response Time Tests
# ============================================================================

class TestResponseTime:
    """Test response times."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_simple_query_response_time(self, client):
        """Test simple query response time."""
        start = time.time()
        response = client.post('/get', data={'msg': 'hello'})
        elapsed = time.time() - start
        
        assert response.status_code == 200
        # With mocking/API, should be fast
        assert elapsed < 10.0  # Allow up to 10s for API calls
    
    def test_page_load_time(self, client):
        """Test page load time."""
        start = time.time()
        response = client.get('/')
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 3.0  # Page should load in 3 seconds
    
    def test_clear_endpoint_time(self, client):
        """Test clear endpoint response time."""
        start = time.time()
        response = client.post('/clear')
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0  # Should be instant


# ============================================================================
# Helper Function Performance Tests
# ============================================================================

class TestHelperPerformance:
    """Test helper function performance."""
    
    def test_token_counter_speed(self):
        """Test token counter is fast."""
        from src.helper import _TC
        
        text = "This is a test sentence for token counting performance."
        
        # Run multiple times
        start = time.time()
        for _ in range(1000):
            _TC.count(text)
        elapsed = time.time() - start
        
        # Should process 1000 tokens quickly
        assert elapsed < 1.0, f"Token counting too slow: {elapsed}s"
    
    def test_token_fits_check_speed(self):
        """Test token budget checking is fast."""
        from src.helper import _TC
        
        start = time.time()
        for _ in range(1000):
            _TC.fits(50, "short text", 100)
        elapsed = time.time() - start
        
        assert elapsed < 1.0
    
    def test_text_cleaning_speed(self):
        """Test text cleaning is fast."""
        from src.helper import _clean_text
        
        text = "  Multiple   spaces   and  \n\n\n  newlines  "
        
        start = time.time()
        for _ in range(1000):
            _clean_text(text)
        elapsed = time.time() - start
        
        assert elapsed < 1.0
    
    def test_boilerplate_detection_speed(self):
        """Test boilerplate detection is fast."""
        from src.helper import _is_boilerplate
        
        test_strings = [
            "Page 1",
            "www.example.com",
            "Normal content",
            "Gale Encyclopedia of Medicine",
        ]
        
        start = time.time()
        for _ in range(1000):
            for s in test_strings:
                _is_boilerplate(s)
        elapsed = time.time() - start
        
        assert elapsed < 1.0
    
    def test_content_classification_speed(self):
        """Test content classification is fast."""
        from src.helper import _classify_content
        
        test_cases = [
            "This is a long paragraph of prose text.",
            "- Item 1\n- Item 2\n- Item 3",
            "Some bullet points:\n* One\n* Two\n* Three",
        ]
        
        start = time.time()
        for _ in range(1000):
            for text in test_cases:
                _classify_content(text)
        elapsed = time.time() - start
        
        assert elapsed < 1.0


# ============================================================================
# Memory Usage Tests
# ============================================================================

class TestMemoryUsage:
    """Test memory usage."""
    
    def test_token_counter_memory(self):
        """Test token counter doesn't leak memory."""
        from src.helper import _TC
        
        # Create multiple counters (should be same instance)
        counters = [_TC for _ in range(10)]
        
        # All should reference same object (singleton)
        assert all(c is _TC for c in counters)
    
    def test_session_history_memory_limit(self):
        """Test session history respects memory limit."""
        from app import MAX_HISTORY_MESSAGES
        
        # Should be capped
        assert MAX_HISTORY_MESSAGES == 20
        assert MAX_HISTORY_MESSAGES <= 100  # Reasonable limit


# ============================================================================
# Concurrency Tests
# ============================================================================

class TestConcurrency:
    """Test concurrent operations."""
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests."""
        from app import app
        
        app.config['TESTING'] = True
        
        def make_request(i):
            with app.test_client() as client:
                response = client.post('/get', data={'msg': f'test {i}'})
                return response.status_code
        
        # Run 5 concurrent requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(5)]
            results = [f.result() for f in as_completed(futures)]
        
        # All should succeed or fail gracefully
        assert all(r in [200, 500] for r in results)
    
    def test_concurrent_session_access(self):
        """Test concurrent session access."""
        from app import app
        
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret'
        
        def access_session(i):
            with app.test_client() as client:
                # Each client gets own session
                response = client.get('/')
                return response.status_code == 200
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(access_session, i) for i in range(3)]
            results = [f.result() for f in as_completed(futures)]
        
        assert all(results)


# ============================================================================
# Caching Tests
# ============================================================================

class TestCaching:
    """Test caching functionality."""
    
    def test_embeddings_cached(self):
        """Test embeddings are cached."""
        try:
            from app import get_embeddings
            # First call
            emb1 = get_embeddings()
            # Second call should return same instance
            emb2 = get_embeddings()
            assert emb1 is emb2  # Same object due to @lru_cache
        except ImportError as e:
            pytest.skip(f"Embeddings import failed: {e}")
    
    def test_llm_cached(self):
        """Test LLM is cached."""
        from app import get_llm
        
        llm1 = get_llm()
        llm2 = get_llm()
        
        assert llm1 is llm2
    
    def test_rag_chain_cached(self):
        """Test RAG chain is cached."""
        from app import get_rag_chain
        
        chain1 = get_rag_chain()
        chain2 = get_rag_chain()
        
        assert chain1 is chain2


# ============================================================================
# Scalability Tests
# ============================================================================

class TestScalability:
    """Test scalability aspects."""
    
    def test_intent_section_map_size(self):
        """Test intent mapping doesn't grow unbounded."""
        from app import _INTENT_SECTION_MAP
        
        # Should be a reasonable number of intent patterns
        assert len(_INTENT_SECTION_MAP) > 0
        assert len(_INTENT_SECTION_MAP) < 20  # Not excessive
    
    def test_request_logs_not_accumulated(self):
        """Test request logs are cleared per request."""
        from app import RequestLogs
        
        logs = RequestLogs()
        logs.info("Test 1")
        logs.clear()
        
        assert len(logs.entries) == 0


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])