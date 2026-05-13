import sys
import os
from unittest.mock import MagicMock, patch

# --- 1. ISOLATION LAYER ---
# Mock problematic libraries BEFORE importing app
mock_groq = MagicMock()
mock_pinecone = MagicMock()
sys.modules['langchain_groq'] = mock_groq
sys.modules['langchain_pinecone'] = mock_pinecone
sys.modules['pinecone'] = MagicMock()
sys.modules['langchain_community.cross_encoders'] = MagicMock()
sys.modules['langchain_community.retrievers'] = MagicMock()
sys.modules['langchain.retrievers'] = MagicMock()
sys.modules['langchain.retrievers.document_compressors'] = MagicMock()

# Ensure we can find the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app
import pytest

class TestFlaskApp:
    @pytest.fixture(scope="class")
    def flask_app(self):
        app.app.config['TESTING'] = True
        return app.app

    @pytest.fixture
    def client(self, flask_app):
        return flask_app.test_client()

    def test_index_route(self, client):
        response = client.get('/')
        assert response.status_code == 200

    def test_health_endpoint(self, client):
        response = client.get('/health')
        assert response.status_code == 200
        assert response.get_json() == {"status": "ok"}

    def test_clear_route(self, client):
        response = client.post('/clear')
        assert response.status_code == 200

class TestHelperFunctions:
    def test_request_logs(self):
        from app import request_logs
        request_logs.clear()
        request_logs.info("smoke test")
        assert len(request_logs.entries) == 1

class TestConfiguration:
    def test_constants(self):
        from app import MAX_HISTORY_MESSAGES, ENABLE_EXTRACTOR, _INTENT_SECTION_MAP
        assert MAX_HISTORY_MESSAGES == 20
        assert isinstance(ENABLE_EXTRACTOR, bool)
        assert _INTENT_SECTION_MAP is not None